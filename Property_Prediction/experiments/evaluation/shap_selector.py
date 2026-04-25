"""
SHAP 기반 FS2 (상위 feature) 선택

GBM 3개 모델(XGB, LGB, CatBoost) × 3타겟의 SHAP importance를 평균내어
상위 N개 feature를 FS2로 확정한다.

저장:
  results/shap/{model}_{target}_shap_values.csv
  results/shap/{model}_{target}_shap_summary.png
  results/shap/fs2_features.json   ← FS2 feature 목록
"""
from __future__ import annotations
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def _shap_importance(model, X: np.ndarray, feature_cols: list[str]) -> pd.Series:
    """TreeExplainer로 feature importance 계산. Series(index=feature_cols) 반환."""
    import shap
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    mean_abs = np.abs(shap_values).mean(axis=0)
    return pd.Series(mean_abs, index=feature_cols)


def compute_fs2(
    df_train: pd.DataFrame,
    feature_cols: list[str],
    targets: list[str],
    results_dir: Path,
    top_n: int = 50,
) -> list[str]:
    """
    XGB / LGB / CatBoost 모델을 전체 train으로 재학습 후 SHAP importance 계산.
    타겟 3개 × 모델 3개의 importance를 평균 → 상위 top_n개를 FS2로 반환.
    """
    from xgboost import XGBRegressor
    from lightgbm import LGBMRegressor
    from catboost import CatBoostRegressor

    shap_dir = results_dir / "shap"
    shap_dir.mkdir(parents=True, exist_ok=True)

    X = df_train[feature_cols].values.astype(float)
    importance_all: list[pd.Series] = []

    gbm_configs = [
        ("XGBoost", XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=6,
                                  subsample=0.8, colsample_bytree=0.8,
                                  random_state=42, n_jobs=-1, verbosity=0)),
        ("LightGBM", LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=63,
                                    min_child_samples=5, subsample=0.8,
                                    colsample_bytree=0.8, random_state=42,
                                    n_jobs=-1, verbose=-1)),
        ("CatBoost", CatBoostRegressor(iterations=500, learning_rate=0.05,
                                        depth=6, random_seed=42, verbose=0)),
    ]

    for target in targets:
        y = df_train[target].values.astype(float)
        for model_name, model in gbm_configs:
            logger.info("SHAP: %s | %s 학습 중...", model_name, target)
            model.fit(X, y)

            imp = _shap_importance(model, X, feature_cols)
            importance_all.append(imp)

            # 개별 저장
            imp.sort_values(ascending=False).to_csv(
                shap_dir / f"{model_name}_{target}_shap_importance.csv", header=["shap_mean_abs"]
            )

            # Top-20 bar plot
            top20 = imp.nlargest(20)
            fig, ax = plt.subplots(figsize=(7, 6))
            ax.barh(top20.index[::-1], top20.values[::-1], color="steelblue", alpha=0.8)
            ax.set_title(f"{model_name} | {target} — SHAP Top-20")
            ax.set_xlabel("mean |SHAP|")
            fig.tight_layout()
            fig.savefig(shap_dir / f"{model_name}_{target}_shap_summary.png", dpi=120)
            plt.close(fig)

    # 전체 평균 importance
    combined = pd.concat(importance_all, axis=1).mean(axis=1)
    combined.sort_values(ascending=False, inplace=True)
    combined.to_csv(shap_dir / "combined_shap_importance.csv", header=["shap_mean_abs"])

    # FS2: 상위 top_n
    fs2_features = combined.head(top_n).index.tolist()
    with open(shap_dir / "fs2_features.json", "w") as f:
        json.dump({"top_n": top_n, "features": fs2_features}, f, indent=2)

    logger.info("FS2 확정: %d개 feature (top_%d)", len(fs2_features), top_n)

    # Combined top-30 bar plot
    top30 = combined.head(30)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.barh(top30.index[::-1], top30.values[::-1], color="darkorange", alpha=0.8)
    ax.set_title(f"Combined SHAP Importance (GBM×3 | Target×3) — Top 30")
    ax.set_xlabel("mean |SHAP|")
    fig.tight_layout()
    fig.savefig(shap_dir / "combined_shap_top30.png", dpi=150)
    plt.close(fig)

    return fs2_features
