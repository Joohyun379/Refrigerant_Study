"""
Parity plot (예측값 vs 실제값) 생성 유틸리티
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


_TARGET_UNITS = {
    "Tc_K":   "K",
    "Pc_MPa": "MPa",
    "omega":  "",
}


def parity_plot(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    target: str,
    model_name: str,
    metrics: dict[str, float],
    save_path: Path | None = None,
) -> plt.Figure:
    unit = _TARGET_UNITS.get(target, "")
    label = f"{target} [{unit}]" if unit else target

    fig, ax = plt.subplots(figsize=(5, 5))

    lo = min(y_true.min(), y_pred.min())
    hi = max(y_true.max(), y_pred.max())
    margin = (hi - lo) * 0.05
    lim = (lo - margin, hi + margin)

    ax.scatter(y_true, y_pred, alpha=0.5, s=20, edgecolors="none", color="steelblue")
    ax.plot(lim, lim, "k--", lw=1, label="y = x")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel(f"True {label}")
    ax.set_ylabel(f"Predicted {label}")
    ax.set_title(f"{model_name} — {target}")

    info = (
        f"RMSE={metrics['rmse']:.3f}  MAE={metrics['mae']:.3f}\n"
        f"R²={metrics['r2']:.3f}  MAPE={metrics['mape']:.1f}%"
    )
    ax.text(0.04, 0.96, info, transform=ax.transAxes,
            va="top", ha="left", fontsize=8,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))
    ax.legend(fontsize=8)

    fig.tight_layout()
    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150)
    return fig
