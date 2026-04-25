"""
Pretrained Language Model 기반 회귀 모델 (Phase 1-E).

ChemBERTaRegressor:
  - backbone: seyonec/ChemBERTa-zinc-base-v1 (RoBERTa 기반, 화학 SMILES 사전학습)
  - 소규모 데이터(476개) 과적합 방지를 위해 backbone은 동결하고 regression head만 학습
  - 필요시 last_unfreeze_layers 개의 transformer layer를 함께 fine-tune
  - X: SMILES 문자열 배열 (dtype=object)
  - FS6 전용
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset

from experiments.models.base import BaseRegressor

MODEL_NAME = "seyonec/ChemBERTa-zinc-base-v1"
MAX_LENGTH = 128


class _SMILESDataset(Dataset):
    def __init__(self, smiles: list[str], y: np.ndarray, tokenizer):
        enc = tokenizer(
            smiles,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        self.input_ids      = enc["input_ids"]
        self.attention_mask = enc["attention_mask"]
        self.y = torch.tensor(y, dtype=torch.float)

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return (
            self.input_ids[idx],
            self.attention_mask[idx],
            self.y[idx],
        )


class ChemBERTaRegressor(BaseRegressor):
    """
    ChemBERTa (frozen backbone) + MLP regression head.

    Parameters
    ----------
    last_unfreeze_layers : 백본에서 추가로 fine-tune할 마지막 transformer layer 수
        0 → backbone 완전 동결 (head만 학습)
        N → 마지막 N개 layer + head 학습
    hidden_dim : regression head 은닉층 크기
    """
    name = "ChemBERTa"
    is_graph_model = True   # SMILES 입력 경로 사용

    def __init__(
        self,
        last_unfreeze_layers: int = 0,
        hidden_dim: int = 256,
        dropout: float = 0.1,
        lr: float = 1e-4,
        head_lr: float = 1e-3,
        weight_decay: float = 1e-4,
        max_epochs: int = 100,
        patience: int = 15,
        batch_size: int = 32,
        random_state: int = 42,
    ):
        self.last_unfreeze_layers = last_unfreeze_layers
        self.hidden_dim           = hidden_dim
        self.dropout              = dropout
        self.lr                   = lr
        self.head_lr              = head_lr
        self.weight_decay         = weight_decay
        self.max_epochs           = max_epochs
        self.patience             = patience
        self.batch_size           = batch_size
        self.random_state         = random_state
        self._y_scaler            = StandardScaler()
        self._device              = torch.device("cpu")
        self._backbone            = None
        self._tokenizer           = None
        self._head                = None

    def _load_backbone(self):
        import warnings
        from transformers import AutoTokenizer, AutoModel
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tok = AutoTokenizer.from_pretrained(MODEL_NAME)
            backbone = AutoModel.from_pretrained(MODEL_NAME)

        # backbone 동결
        for param in backbone.parameters():
            param.requires_grad = False

        # 마지막 N개 layer 해동
        if self.last_unfreeze_layers > 0:
            layers = backbone.encoder.layer
            for layer in layers[-self.last_unfreeze_layers:]:
                for param in layer.parameters():
                    param.requires_grad = True

        return tok, backbone

    def _build_head(self, input_dim: int) -> nn.Module:
        return nn.Sequential(
            nn.Linear(input_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.hidden_dim, self.hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.hidden_dim // 2, 1),
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> "ChemBERTaRegressor":
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        smiles = X.ravel().tolist()
        y_scaled = self._y_scaler.fit_transform(y.reshape(-1, 1)).ravel()

        self._tokenizer, self._backbone = self._load_backbone()
        self._backbone = self._backbone.to(self._device)
        hidden_size = self._backbone.config.hidden_size  # 768

        self._head = self._build_head(hidden_size).to(self._device)

        # train/val 분할
        idx = np.arange(len(smiles))
        idx_tr, idx_va = train_test_split(
            idx, test_size=0.1, random_state=self.random_state
        )
        smi_tr = [smiles[i] for i in idx_tr]
        smi_va = [smiles[i] for i in idx_va]

        ds_tr = _SMILESDataset(smi_tr, y_scaled[idx_tr], self._tokenizer)
        ds_va = _SMILESDataset(smi_va, y_scaled[idx_va], self._tokenizer)
        tr_loader = DataLoader(ds_tr, batch_size=self.batch_size, shuffle=True)
        va_loader = DataLoader(ds_va, batch_size=self.batch_size, shuffle=False)

        # 파라미터 그룹 분리
        head_params = list(self._head.parameters())
        backbone_params = [p for p in self._backbone.parameters() if p.requires_grad]
        param_groups = [{"params": head_params, "lr": self.head_lr}]
        if backbone_params:
            param_groups.append({"params": backbone_params, "lr": self.lr})

        optimizer = torch.optim.AdamW(param_groups, weight_decay=self.weight_decay)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=8
        )
        criterion = nn.MSELoss()

        best_val, best_head_state, patience_cnt = float("inf"), None, 0

        for epoch in range(self.max_epochs):
            self._backbone.train() if backbone_params else self._backbone.eval()
            self._head.train()
            for input_ids, attn_mask, yb in tr_loader:
                input_ids  = input_ids.to(self._device)
                attn_mask  = attn_mask.to(self._device)
                yb         = yb.to(self._device)
                optimizer.zero_grad()
                out = self._backbone(input_ids=input_ids, attention_mask=attn_mask)
                cls = out.last_hidden_state[:, 0, :]
                pred = self._head(cls).squeeze(-1)
                loss = criterion(pred, yb)
                loss.backward()
                nn.utils.clip_grad_norm_(
                    list(self._head.parameters()) + backbone_params, 1.0
                )
                optimizer.step()

            self._backbone.eval()
            self._head.eval()
            val_loss = 0.0
            with torch.no_grad():
                for input_ids, attn_mask, yb in va_loader:
                    input_ids = input_ids.to(self._device)
                    attn_mask = attn_mask.to(self._device)
                    yb        = yb.to(self._device)
                    out  = self._backbone(input_ids=input_ids, attention_mask=attn_mask)
                    cls  = out.last_hidden_state[:, 0, :]
                    pred = self._head(cls).squeeze(-1)
                    val_loss += criterion(pred, yb).item()
            val_loss /= max(len(va_loader), 1)
            scheduler.step(val_loss)

            if val_loss < best_val - 1e-6:
                best_val = val_loss
                best_head_state = {k: v.cpu().clone() for k, v in self._head.state_dict().items()}
                patience_cnt = 0
            else:
                patience_cnt += 1
                if patience_cnt >= self.patience:
                    break

        if best_head_state is not None:
            self._head.load_state_dict(best_head_state)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        smiles = X.ravel().tolist()
        enc = self._tokenizer(
            smiles,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        self._backbone.eval()
        self._head.eval()
        preds = []
        # 배치 처리
        n = len(smiles)
        bs = self.batch_size
        with torch.no_grad():
            for start in range(0, n, bs):
                ids  = enc["input_ids"][start:start+bs].to(self._device)
                mask = enc["attention_mask"][start:start+bs].to(self._device)
                out  = self._backbone(input_ids=ids, attention_mask=mask)
                cls  = out.last_hidden_state[:, 0, :]
                preds.append(self._head(cls).squeeze(-1).cpu().numpy())
        preds_np = np.concatenate(preds, axis=0)
        return self._y_scaler.inverse_transform(preds_np.reshape(-1, 1)).ravel()

    def get_params(self) -> dict:
        return {
            "model_name":           MODEL_NAME,
            "last_unfreeze_layers": self.last_unfreeze_layers,
            "hidden_dim":           self.hidden_dim,
            "lr":                   self.lr,
            "head_lr":              self.head_lr,
            "max_epochs":           self.max_epochs,
            "patience":             self.patience,
        }
