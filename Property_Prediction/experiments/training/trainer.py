"""
Phase 1 CV 학습 루프

사용 흐름:
    trainer = Trainer(df_train, feature_cols, results_dir)
    result  = trainer.run(model, target)
"""
from __future__ import annotations
import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.configs.base import RANDOM_STATE, RESULTS_DIR
from experiments.evaluation.metrics import compute_metrics
from experiments.evaluation.parity_plot import parity_plot
from experiments.training.cross_validation import get_cv_splits

logger = logging.getLogger(__name__)


class Trainer:
    def __init__(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        results_dir: Path = RESULTS_DIR,
        save_plots: bool = True,
    ):
        self.df = df.reset_index(drop=True)
        self.feature_cols = feature_cols
        self.results_dir = Path(results_dir)
        self.save_plots = save_plots
        self._splits = get_cv_splits(self.df)

    # ──────────────────────────────────────────────────────────────────────
    def run(self, model, target: str) -> dict:
        """
        5-fold CV 수행 후 결과 딕셔너리 반환.

        Returns
        -------
        {
          "model": str,
          "target": str,
          "feature_set": str,   ← model에 fs 속성이 있으면 사용
          "cv_metrics": [{"fold": int, "rmse": float, ...}, ...],
          "mean_metrics": {"rmse": float, ...},
          "std_metrics":  {"rmse": float, ...},
          "oof_true": [...],
          "oof_pred": [...],
        }
        """
        is_graph = getattr(model, "is_graph_model", False)
        if is_graph:
            # GNN: feature_cols = ['SMILES'], X_all은 문자열 배열
            X_all = self.df[self.feature_cols].values  # dtype=object
        else:
            X_all = self.df[self.feature_cols].values.astype(float)
        y_all = self.df[target].values.astype(float)

        oof_true = np.empty(len(self.df))
        oof_pred = np.empty(len(self.df))
        cv_metrics = []

        t0 = time.time()
        for fold, (tr_idx, va_idx) in enumerate(self._splits):
            X_tr, y_tr = X_all[tr_idx], y_all[tr_idx]
            X_va, y_va = X_all[va_idx], y_all[va_idx]

            model.fit(X_tr, y_tr)
            preds = model.predict(X_va)

            oof_true[va_idx] = y_va
            oof_pred[va_idx] = preds

            fold_metrics = compute_metrics(y_va, preds, target)
            fold_metrics["fold"] = fold
            cv_metrics.append(fold_metrics)
            logger.info(
                "[%s | %s | fold %d] RMSE=%.4f  R²=%.4f  MAPE=%.2f%%",
                model.name, target, fold,
                fold_metrics["rmse"], fold_metrics["r2"], fold_metrics["mape"],
            )

        elapsed = time.time() - t0

        # 평균/표준편차
        metric_keys = ["rmse", "mae", "mape", "r2", "nrmse"]
        mean_m = {k: float(np.mean([m[k] for m in cv_metrics])) for k in metric_keys}
        std_m  = {k: float(np.std( [m[k] for m in cv_metrics])) for k in metric_keys}

        logger.info(
            "[%s | %s] CV done in %.1fs — RMSE=%.4f±%.4f  R²=%.4f±%.4f",
            model.name, target, elapsed,
            mean_m["rmse"], std_m["rmse"],
            mean_m["r2"],   std_m["r2"],
        )

        result = {
            "model":        model.name,
            "target":       target,
            "feature_set":  getattr(model, "fs", "unknown"),
            "params":       model.get_params(),
            "elapsed_s":    round(elapsed, 2),
            "cv_metrics":   cv_metrics,
            "mean_metrics": mean_m,
            "std_metrics":  std_m,
            "oof_true":     oof_true.tolist(),
            "oof_pred":     oof_pred.tolist(),
        }

        # 저장
        self._save_result(result, model, target)
        return result

    # ──────────────────────────────────────────────────────────────────────
    def _save_result(self, result: dict, model, target: str):
        tag = f"{model.name}_{getattr(model, 'fs', 'fs?')}_{target}"

        # JSON (cv_scores)
        json_dir = self.results_dir / "cv_scores"
        json_dir.mkdir(parents=True, exist_ok=True)
        with open(json_dir / f"{tag}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # OOF 예측값 CSV
        pred_dir = self.results_dir / "predictions"
        pred_dir.mkdir(parents=True, exist_ok=True)
        oof_df = pd.DataFrame({
            "true": result["oof_true"],
            "pred": result["oof_pred"],
        })
        oof_df.to_csv(pred_dir / f"{tag}_oof.csv", index=False)

        # Parity plot
        if self.save_plots:
            plot_path = self.results_dir / "plots" / f"{tag}_parity.png"
            parity_plot(
                np.array(result["oof_true"]),
                np.array(result["oof_pred"]),
                target=target,
                model_name=model.name,
                metrics=result["mean_metrics"],
                save_path=plot_path,
            )
