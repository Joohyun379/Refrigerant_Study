"""
Phase 1-C: NN-Tabular 모델
  - TabNet  (pytorch-tabnet)
  - FT-Transformer (직접 구현, Gorishniy et al. 2021)

두 모델 모두 BaseRegressor 인터페이스(fit / predict)를 준수.
내부적으로 StandardScaler 전처리 포함.
"""
from __future__ import annotations
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from .base import BaseRegressor


# ══════════════════════════════════════════════════════════════════════════════
# 1. TabNet
# ══════════════════════════════════════════════════════════════════════════════
class TabNetRegressor(BaseRegressor):
    """pytorch-tabnet 래퍼."""
    name = "TabNet"

    def __init__(
        self,
        n_d: int = 32,
        n_a: int = 32,
        n_steps: int = 3,
        gamma: float = 1.3,
        n_shared: int = 2,
        lambda_sparse: float = 1e-3,
        lr: float = 2e-2,
        max_epochs: int = 200,
        patience: int = 20,
        batch_size: int = 256,
        random_state: int = 42,
    ):
        self.n_d = n_d
        self.n_a = n_a
        self.n_steps = n_steps
        self.gamma = gamma
        self.n_shared = n_shared
        self.lambda_sparse = lambda_sparse
        self.lr = lr
        self.max_epochs = max_epochs
        self.patience = patience
        self.batch_size = batch_size
        self.random_state = random_state
        self._scaler = StandardScaler()

    def fit(self, X: np.ndarray, y: np.ndarray) -> "TabNetRegressor":
        from pytorch_tabnet.tab_model import TabNetRegressor as _TN

        X_s = self._scaler.fit_transform(X).astype(np.float32)
        y_r = y.reshape(-1, 1).astype(np.float32)

        X_tr, X_va, y_tr, y_va = train_test_split(
            X_s, y_r, test_size=0.1, random_state=self.random_state
        )

        self._model = _TN(
            n_d=self.n_d, n_a=self.n_a,
            n_steps=self.n_steps, gamma=self.gamma,
            n_shared=self.n_shared,
            lambda_sparse=self.lambda_sparse,
            optimizer_fn=torch.optim.Adam,
            optimizer_params={"lr": self.lr},
            scheduler_fn=torch.optim.lr_scheduler.StepLR,
            scheduler_params={"step_size": 50, "gamma": 0.5},
            mask_type="entmax",
            seed=self.random_state,
            verbose=0,
        )
        self._model.fit(
            X_train=X_tr, y_train=y_tr,
            eval_set=[(X_va, y_va)],
            eval_name=["val"],
            eval_metric=["rmse"],
            max_epochs=self.max_epochs,
            patience=self.patience,
            batch_size=self.batch_size,
            virtual_batch_size=min(128, self.batch_size),
            drop_last=False,
        )
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X_s = self._scaler.transform(X).astype(np.float32)
        return self._model.predict(X_s).flatten()

    def get_params(self) -> dict:
        return {"n_d": self.n_d, "n_steps": self.n_steps, "lr": self.lr}


# ══════════════════════════════════════════════════════════════════════════════
# 2. FT-Transformer
# ══════════════════════════════════════════════════════════════════════════════
class _FeatureTokenizer(nn.Module):
    """각 수치 feature를 d_model 차원 임베딩으로 변환."""
    def __init__(self, n_features: int, d_model: int):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(n_features, d_model))
        self.bias   = nn.Parameter(torch.zeros(n_features, d_model))
        nn.init.kaiming_uniform_(self.weight, a=0.01)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, F)  → (B, F, d_model)
        return x.unsqueeze(-1) * self.weight.unsqueeze(0) + self.bias.unsqueeze(0)


class _FTTBlock(nn.Module):
    """FT-Transformer 블록: Pre-LN Multi-Head Attention + FFN."""
    def __init__(self, d_model: int, n_heads: int, d_ffn: int, dropout: float):
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.attn  = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn   = nn.Sequential(
            nn.Linear(d_model, d_ffn),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ffn, d_model),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.norm1(x)
        h, _ = self.attn(h, h, h)
        x = x + h
        h = self.norm2(x)
        h = self.ffn(h)
        return x + h


class _FTTransformerNet(nn.Module):
    def __init__(
        self,
        n_features: int,
        d_model: int = 128,
        n_heads: int = 8,
        n_layers: int = 3,
        d_ffn_factor: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        d_ffn = d_model * d_ffn_factor

        self.tokenizer = _FeatureTokenizer(n_features, d_model)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))

        self.blocks = nn.ModuleList([
            _FTTBlock(d_model, n_heads, d_ffn, dropout)
            for _ in range(n_layers)
        ])
        self.norm = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B = x.size(0)
        tokens = self.tokenizer(x)                            # (B, F, d)
        cls = self.cls_token.expand(B, -1, -1)               # (B, 1, d)
        tokens = torch.cat([cls, tokens], dim=1)              # (B, F+1, d)
        for block in self.blocks:
            tokens = block(tokens)
        cls_out = self.norm(tokens[:, 0])                     # (B, d)
        return self.head(cls_out).squeeze(-1)                 # (B,)


class FTTransformerRegressor(BaseRegressor):
    """FT-Transformer (Gorishniy et al., 2021) sklearn 인터페이스 래퍼."""
    name = "FTTransformer"

    def __init__(
        self,
        d_model: int = 64,
        n_heads: int = 4,
        n_layers: int = 2,
        d_ffn_factor: int = 4,
        dropout: float = 0.1,
        lr: float = 1e-4,
        weight_decay: float = 1e-5,
        max_epochs: int = 50,
        patience: int = 10,
        batch_size: int = 256,
        random_state: int = 42,
    ):
        self.d_model = d_model
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.d_ffn_factor = d_ffn_factor
        self.dropout = dropout
        self.lr = lr
        self.weight_decay = weight_decay
        self.max_epochs = max_epochs
        self.patience = patience
        self.batch_size = batch_size
        self.random_state = random_state
        self._scaler = StandardScaler()
        self._y_scaler = StandardScaler()
        self._device = torch.device("cpu")

    def fit(self, X: np.ndarray, y: np.ndarray) -> "FTTransformerRegressor":
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        X_s = self._scaler.fit_transform(X).astype(np.float32)
        y_f = self._y_scaler.fit_transform(y.reshape(-1, 1)).ravel().astype(np.float32)

        X_tr, X_va, y_tr, y_va = train_test_split(
            X_s, y_f, test_size=0.1, random_state=self.random_state
        )

        n_features = X_s.shape[1]
        # n_heads가 d_model을 나눌 수 있도록 조정
        n_heads = self.n_heads
        while self.d_model % n_heads != 0:
            n_heads -= 1

        self._net = _FTTransformerNet(
            n_features=n_features,
            d_model=self.d_model,
            n_heads=n_heads,
            n_layers=self.n_layers,
            d_ffn_factor=self.d_ffn_factor,
            dropout=self.dropout,
        ).to(self._device)

        optimizer = torch.optim.AdamW(
            self._net.parameters(), lr=self.lr, weight_decay=self.weight_decay
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=self.max_epochs
        )
        criterion = nn.MSELoss()

        tr_loader = DataLoader(
            TensorDataset(
                torch.from_numpy(X_tr),
                torch.from_numpy(y_tr),
            ),
            batch_size=self.batch_size, shuffle=True, drop_last=False,
        )
        X_va_t = torch.from_numpy(X_va).to(self._device)
        y_va_t = torch.from_numpy(y_va).to(self._device)

        best_val = float("inf")
        best_state = None
        patience_cnt = 0

        for epoch in range(self.max_epochs):
            self._net.train()
            for xb, yb in tr_loader:
                xb, yb = xb.to(self._device), yb.to(self._device)
                optimizer.zero_grad()
                loss = criterion(self._net(xb), yb)
                loss.backward()
                nn.utils.clip_grad_norm_(self._net.parameters(), 1.0)
                optimizer.step()
            scheduler.step()

            self._net.eval()
            with torch.no_grad():
                val_loss = criterion(self._net(X_va_t), y_va_t).item()

            if val_loss < best_val - 1e-6:
                best_val = val_loss
                best_state = {k: v.cpu().clone() for k, v in self._net.state_dict().items()}
                patience_cnt = 0
            else:
                patience_cnt += 1
                if patience_cnt >= self.patience:
                    break

        if best_state is not None:
            self._net.load_state_dict(best_state)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X_s = self._scaler.transform(X).astype(np.float32)
        self._net.eval()
        with torch.no_grad():
            preds = self._net(torch.from_numpy(X_s).to(self._device))
        preds_np = preds.cpu().numpy()
        return self._y_scaler.inverse_transform(preds_np.reshape(-1, 1)).ravel()

    def get_params(self) -> dict:
        return {
            "d_model": self.d_model,
            "n_heads": self.n_heads,
            "n_layers": self.n_layers,
            "lr": self.lr,
        }
