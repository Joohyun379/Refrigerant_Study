"""
GNN 계열 모델 (Phase 1-D).

모든 모델은 X로 SMILES 문자열 배열(np.ndarray, dtype=object)을 받는다.
내부적으로 PyG Data 로 변환 후 학습/예측한다.

구현 모델:
  - GCNRegressor     : GCNConv (Kipf & Welling, 2017)
  - GATRegressor     : GATConv (Velickovic et al., 2018)
  - GINRegressor     : GINConv (Xu et al., 2019)
  - AttentiveFPRegressor : AttentiveFP (Xiong et al., 2020)
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch_geometric.nn import (
    GCNConv, GATConv, GINConv,
    global_mean_pool, global_add_pool,
)

from experiments.models.base import BaseRegressor
from experiments.models.smiles_to_graph import smiles_to_dataset

# AttentiveFP는 선택적 import (구버전 PyG 호환)
try:
    from torch_geometric.nn import AttentiveFP as _AttentiveFP
    _HAS_AFP = True
except ImportError:
    _HAS_AFP = False

ATOM_DIM = 24   # cat2_local_graph.py 기준 (node_dim)
EDGE_DIM = 9    # cat2_local_graph.py 기준 (edge_dim)


# ─── 공통 베이스 ─────────────────────────────────────────────────────────────

class _BaseGNN(BaseRegressor):
    """SMILES 배열을 받아 PyG 그래프로 변환 후 학습하는 GNN 공통 클래스."""

    is_graph_model: bool = True   # trainer가 SMILES 경로임을 인지

    def __init__(
        self,
        hidden_dim: int = 128,
        n_layers: int = 3,
        dropout: float = 0.1,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        max_epochs: int = 200,
        patience: int = 20,
        batch_size: int = 32,
        random_state: int = 42,
    ):
        self.hidden_dim   = hidden_dim
        self.n_layers     = n_layers
        self.dropout      = dropout
        self.lr           = lr
        self.weight_decay = weight_decay
        self.max_epochs   = max_epochs
        self.patience     = patience
        self.batch_size   = batch_size
        self.random_state = random_state
        self._y_scaler    = StandardScaler()
        self._device      = torch.device("cpu")
        self._net: nn.Module | None = None

    # 서브클래스에서 구현
    def _build_net(self) -> nn.Module:
        raise NotImplementedError

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_BaseGNN":
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        smiles = X.ravel().tolist()
        y_scaled = self._y_scaler.fit_transform(y.reshape(-1, 1)).ravel()

        # train / val 분할 (인덱스 기반)
        idx = np.arange(len(smiles))
        idx_tr, idx_va = train_test_split(
            idx, test_size=0.1, random_state=self.random_state
        )

        ds_tr = smiles_to_dataset(
            [smiles[i] for i in idx_tr], y_scaled[idx_tr]
        )
        ds_va = smiles_to_dataset(
            [smiles[i] for i in idx_va], y_scaled[idx_va]
        )

        self._net = self._build_net().to(self._device)
        optimizer = torch.optim.Adam(
            self._net.parameters(), lr=self.lr, weight_decay=self.weight_decay
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=10
        )
        criterion = nn.MSELoss()

        tr_loader = DataLoader(ds_tr, batch_size=self.batch_size, shuffle=True)
        va_loader = DataLoader(ds_va, batch_size=self.batch_size, shuffle=False)

        best_val, best_state, patience_cnt = float("inf"), None, 0
        for epoch in range(self.max_epochs):
            self._net.train()
            for batch in tr_loader:
                batch = batch.to(self._device)
                optimizer.zero_grad()
                pred = self._net(batch)
                loss = criterion(pred, batch.y)
                loss.backward()
                nn.utils.clip_grad_norm_(self._net.parameters(), 1.0)
                optimizer.step()

            self._net.eval()
            val_loss = 0.0
            with torch.no_grad():
                for batch in va_loader:
                    batch = batch.to(self._device)
                    val_loss += criterion(self._net(batch), batch.y).item()
            val_loss /= len(va_loader)
            scheduler.step(val_loss)

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
        smiles = X.ravel().tolist()
        ds = smiles_to_dataset(smiles)
        loader = DataLoader(ds, batch_size=self.batch_size, shuffle=False)

        self._net.eval()
        preds = []
        with torch.no_grad():
            for batch in loader:
                batch = batch.to(self._device)
                preds.append(self._net(batch).cpu().numpy())
        preds_np = np.concatenate(preds, axis=0).ravel()
        return self._y_scaler.inverse_transform(preds_np.reshape(-1, 1)).ravel()

    def get_params(self) -> dict:
        return {
            "hidden_dim": self.hidden_dim,
            "n_layers":   self.n_layers,
            "dropout":    self.dropout,
            "lr":         self.lr,
            "max_epochs": self.max_epochs,
            "patience":   self.patience,
        }


# ─── GCN ─────────────────────────────────────────────────────────────────────

class _GCNNet(nn.Module):
    def __init__(self, in_dim, hidden_dim, n_layers, dropout):
        super().__init__()
        self.convs = nn.ModuleList()
        self.bns   = nn.ModuleList()
        self.convs.append(GCNConv(in_dim, hidden_dim))
        self.bns.append(nn.BatchNorm1d(hidden_dim))
        for _ in range(n_layers - 1):
            self.convs.append(GCNConv(hidden_dim, hidden_dim))
            self.bns.append(nn.BatchNorm1d(hidden_dim))
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, data: Data) -> torch.Tensor:
        x, edge_index, batch = data.x, data.edge_index, data.batch
        for conv, bn in zip(self.convs, self.bns):
            x = bn(torch.relu(conv(x, edge_index)))
            x = self.dropout(x)
        x = global_mean_pool(x, batch)
        return self.head(x).squeeze(-1)


class GCNRegressor(_BaseGNN):
    name = "GCN"

    def _build_net(self) -> nn.Module:
        return _GCNNet(ATOM_DIM, self.hidden_dim, self.n_layers, self.dropout)


# ─── GAT ─────────────────────────────────────────────────────────────────────

class _GATNet(nn.Module):
    def __init__(self, in_dim, hidden_dim, n_layers, dropout, n_heads=4):
        super().__init__()
        assert hidden_dim % n_heads == 0
        head_dim = hidden_dim // n_heads
        self.convs = nn.ModuleList()
        self.bns   = nn.ModuleList()
        self.convs.append(GATConv(in_dim, head_dim, heads=n_heads, dropout=dropout))
        self.bns.append(nn.BatchNorm1d(hidden_dim))
        for _ in range(n_layers - 1):
            self.convs.append(GATConv(hidden_dim, head_dim, heads=n_heads, dropout=dropout))
            self.bns.append(nn.BatchNorm1d(hidden_dim))
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, data: Data) -> torch.Tensor:
        x, edge_index, batch = data.x, data.edge_index, data.batch
        for conv, bn in zip(self.convs, self.bns):
            x = bn(torch.relu(conv(x, edge_index)))
            x = self.dropout(x)
        x = global_mean_pool(x, batch)
        return self.head(x).squeeze(-1)


class GATRegressor(_BaseGNN):
    name = "GAT"

    def __init__(self, n_heads: int = 4, **kwargs):
        super().__init__(**kwargs)
        self.n_heads = n_heads

    def _build_net(self) -> nn.Module:
        return _GATNet(ATOM_DIM, self.hidden_dim, self.n_layers, self.dropout, self.n_heads)

    def get_params(self) -> dict:
        p = super().get_params()
        p["n_heads"] = self.n_heads
        return p


# ─── GIN ─────────────────────────────────────────────────────────────────────

class _GINNet(nn.Module):
    def __init__(self, in_dim, hidden_dim, n_layers, dropout):
        super().__init__()
        self.convs = nn.ModuleList()
        self.bns   = nn.ModuleList()

        def _mlp(din, dout):
            return nn.Sequential(
                nn.Linear(din, dout), nn.BatchNorm1d(dout), nn.ReLU(),
                nn.Linear(dout, dout),
            )

        self.convs.append(GINConv(_mlp(in_dim, hidden_dim), train_eps=True))
        self.bns.append(nn.BatchNorm1d(hidden_dim))
        for _ in range(n_layers - 1):
            self.convs.append(GINConv(_mlp(hidden_dim, hidden_dim), train_eps=True))
            self.bns.append(nn.BatchNorm1d(hidden_dim))
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, data: Data) -> torch.Tensor:
        x, edge_index, batch = data.x, data.edge_index, data.batch
        for conv, bn in zip(self.convs, self.bns):
            x = bn(torch.relu(conv(x, edge_index)))
            x = self.dropout(x)
        x = global_add_pool(x, batch)
        return self.head(x).squeeze(-1)


class GINRegressor(_BaseGNN):
    name = "GIN"

    def _build_net(self) -> nn.Module:
        return _GINNet(ATOM_DIM, self.hidden_dim, self.n_layers, self.dropout)


# ─── AttentiveFP ─────────────────────────────────────────────────────────────

class AttentiveFPRegressor(_BaseGNN):
    """
    PyG의 AttentiveFP 래퍼.
    _HAS_AFP=False인 경우 GCN으로 대체한다.
    """
    name = "AttentiveFP"

    def __init__(self, n_timesteps: int = 2, **kwargs):
        super().__init__(**kwargs)
        self.n_timesteps = n_timesteps

    def _build_net(self) -> nn.Module:
        if not _HAS_AFP:
            import warnings
            warnings.warn("AttentiveFP not available; falling back to GCN.")
            return _GCNNet(ATOM_DIM, self.hidden_dim, self.n_layers, self.dropout)
        return _AttentiveFP(
            in_channels=ATOM_DIM,
            hidden_channels=self.hidden_dim,
            out_channels=1,
            edge_dim=EDGE_DIM,
            num_layers=self.n_layers,
            num_timesteps=self.n_timesteps,
            dropout=self.dropout,
        )

    def forward_override(self, data: Data) -> torch.Tensor:
        # AttentiveFP의 forward 시그니처가 다름 → predict/fit에서 직접 호출
        return self._net(data.x, data.edge_index, data.edge_attr, data.batch)

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not _HAS_AFP:
            return super().predict(X)
        smiles = X.ravel().tolist()
        ds = smiles_to_dataset(smiles)
        loader = DataLoader(ds, batch_size=self.batch_size, shuffle=False)
        self._net.eval()
        preds = []
        with torch.no_grad():
            for batch in loader:
                batch = batch.to(self._device)
                out = self._net(batch.x, batch.edge_index, batch.edge_attr, batch.batch)
                preds.append(out.cpu().numpy())
        preds_np = np.concatenate(preds, axis=0).ravel()
        return self._y_scaler.inverse_transform(preds_np.reshape(-1, 1)).ravel()

    def fit(self, X: np.ndarray, y: np.ndarray) -> "AttentiveFPRegressor":
        if not _HAS_AFP:
            return super().fit(X, y)
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        smiles = X.ravel().tolist()
        y_scaled = self._y_scaler.fit_transform(y.reshape(-1, 1)).ravel()

        idx = np.arange(len(smiles))
        idx_tr, idx_va = train_test_split(idx, test_size=0.1, random_state=self.random_state)
        ds_tr = smiles_to_dataset([smiles[i] for i in idx_tr], y_scaled[idx_tr])
        ds_va = smiles_to_dataset([smiles[i] for i in idx_va], y_scaled[idx_va])

        self._net = self._build_net().to(self._device)
        optimizer = torch.optim.Adam(
            self._net.parameters(), lr=self.lr, weight_decay=self.weight_decay
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=10
        )
        criterion = nn.MSELoss()

        tr_loader = DataLoader(ds_tr, batch_size=self.batch_size, shuffle=True)
        va_loader = DataLoader(ds_va, batch_size=self.batch_size, shuffle=False)

        best_val, best_state, patience_cnt = float("inf"), None, 0
        for epoch in range(self.max_epochs):
            self._net.train()
            for batch in tr_loader:
                batch = batch.to(self._device)
                optimizer.zero_grad()
                pred = self._net(batch.x, batch.edge_index, batch.edge_attr, batch.batch)
                loss = criterion(pred, batch.y)
                loss.backward()
                nn.utils.clip_grad_norm_(self._net.parameters(), 1.0)
                optimizer.step()

            self._net.eval()
            val_loss = 0.0
            with torch.no_grad():
                for batch in va_loader:
                    batch = batch.to(self._device)
                    val_loss += criterion(
                        self._net(batch.x, batch.edge_index, batch.edge_attr, batch.batch),
                        batch.y,
                    ).item()
            val_loss /= max(len(va_loader), 1)
            scheduler.step(val_loss)

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

    def get_params(self) -> dict:
        p = super().get_params()
        p["n_timesteps"] = self.n_timesteps
        return p
