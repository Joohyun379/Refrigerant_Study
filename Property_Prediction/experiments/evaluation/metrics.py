"""
회귀 평가 지표
"""
from __future__ import annotations
import numpy as np
from sklearn.metrics import r2_score

from experiments.configs.base import TARGET_RANGES


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def mape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-8) -> float:
    """Mean Absolute Percentage Error (%)."""
    return float(np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + eps))) * 100)


def nrmse(y_true: np.ndarray, y_pred: np.ndarray, target: str) -> float:
    """Normalized RMSE = RMSE / (max - min) × 100 (%)."""
    r = TARGET_RANGES.get(target, None)
    if r is None or r == 0:
        return float("nan")
    return rmse(y_true, y_pred) / r * 100


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    target: str,
) -> dict[str, float]:
    """타겟 하나에 대한 전체 평가 지표 딕셔너리 반환."""
    return {
        "rmse":  rmse(y_true, y_pred),
        "mae":   mae(y_true, y_pred),
        "mape":  mape(y_true, y_pred),
        "r2":    float(r2_score(y_true, y_pred)),
        "nrmse": nrmse(y_true, y_pred, target),
    }
