"""
Phase 1: Single-output regression
실험설계서(docs/experiment_design.md) 기준 모델별 feature set 자동 할당.

모델별 feature set 할당:
  Ridge, Lasso, SVR-Lin, SVR-RBF, RF, XGB, LGB, CatBoost → FS1 + FS2 + FS3_*
  GP                                                       → FS2 + FS3_* (FS1 제외)
  MLP_sklearn                                              → FS1 + FS2 + FS3_*

실행 예시:
  # 전체 Phase 1-A/B (기준선 + GBM)
  python run2_experiment_phase1.py

  # 특정 모델만
  python run2_experiment_phase1.py --models XGBoost,LightGBM

  # 타겟 하나만
  python run2_experiment_phase1.py --targets Tc_K

  # hold-out test 평가 생략
  python run2_experiment_phase1.py --no-test

  # 기존 결과 건너뜀
  python run2_experiment_phase1.py --skip-existing
"""
from __future__ import annotations
import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.configs.base import RESULTS_DIR, TARGETS
from experiments.configs.feature_sets import build_feature_sets, load_feature_df
from experiments.training.holdout import split_holdout
from experiments.training.trainer import Trainer
from experiments.evaluation.metrics import compute_metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("phase1")


# ── 모델별 FS 할당 정의 ────────────────────────────────────────────────────
_FS3 = ["FS3_gc", "FS3_lg", "FS3_gt", "FS3_rf", "FS3_el"]

MODEL_FS_PLAN: dict[str, list[str]] = {
    # Phase 1-A: Linear / Kernel
    "Ridge":           ["FS1", "FS2"] + _FS3,
    "Lasso":           ["FS1", "FS2"] + _FS3,
    "SVR_Linear":      ["FS1", "FS2"] + _FS3,
    "SVR_RBF":         ["FS1", "FS2"] + _FS3,
    "GP":              ["FS2"] + _FS3,          # FS1(235차원) 제외
    # Phase 1-B: Tree Ensemble
    "RandomForest":    ["FS1", "FS2"] + _FS3,
    "XGBoost":         ["FS1", "FS2"] + _FS3,
    "LightGBM":        ["FS1", "FS2"] + _FS3,
    "CatBoost":        ["FS1", "FS2"] + _FS3,
    # Phase 1-C: NN-Tabular
    "MLP_sklearn":     ["FS1", "FS2"] + _FS3,
    "TabNet":          ["FS1", "FS2"] + _FS3,
    # FTTransformer: 소규모 데이터(476개)에서 GBM 대비 이점 없고 CPU 속도 문제로 제외
    # Phase 1-D: GNN (FS4 = 분자 그래프)
    "GCN":             ["FS4"],
    "GAT":             ["FS4"],
    "GIN":             ["FS4"],
    "AttentiveFP":     ["FS4"],
    # Phase 1-E: Pretrained LM (FS6 = Raw SMILES)
    "ChemBERTa":       ["FS6"],
}


def _build_model(name: str):
    """이름으로 모델 인스턴스 생성."""
    from experiments.models.linear import RidgeRegressor, LassoRegressor, SVRLinear, SVRRBF, GPRegressor
    from experiments.models.gbm import RFRegressor, XGBRegressor, LGBRegressor, CatBoostRegressor_, MLPRegressorModel
    from experiments.models.nn_tabular import TabNetRegressor
    from experiments.models.nn_graph import GCNRegressor, GATRegressor, GINRegressor, AttentiveFPRegressor
    from experiments.models.pretrained_lm import ChemBERTaRegressor

    registry = {
        "Ridge":          RidgeRegressor,
        "Lasso":          LassoRegressor,
        "SVR_Linear":     SVRLinear,
        "SVR_RBF":        SVRRBF,
        "GP":             GPRegressor,
        "RandomForest":   RFRegressor,
        "XGBoost":        XGBRegressor,
        "LightGBM":       LGBRegressor,
        "CatBoost":       CatBoostRegressor_,
        "MLP_sklearn":    MLPRegressorModel,
        "TabNet":         TabNetRegressor,
        "GCN":            GCNRegressor,
        "GAT":            GATRegressor,
        "GIN":            GINRegressor,
        "AttentiveFP":    AttentiveFPRegressor,
        "ChemBERTa":      ChemBERTaRegressor,
    }
    return registry[name]()


# ── FS2 로드 또는 계산 ─────────────────────────────────────────────────────
def get_or_compute_fs2(df_train: pd.DataFrame, feature_cols_fs1: list[str]) -> list[str]:
    fs2_path = RESULTS_DIR / "shap" / "fs2_features.json"
    if fs2_path.exists():
        with open(fs2_path) as f:
            data = json.load(f)
        fs2 = data["features"]
        logger.info("FS2 기존 파일 로드: %d개 feature (%s)", len(fs2), fs2_path)
        return fs2

    logger.info("FS2 미확정 — SHAP 분석 시작...")
    from experiments.evaluation.shap_selector import compute_fs2
    fs2 = compute_fs2(
        df_train=df_train,
        feature_cols=feature_cols_fs1,
        targets=TARGETS,
        results_dir=RESULTS_DIR,
        top_n=50,
    )
    return fs2


# ── 결과 요약 CSV 저장 ─────────────────────────────────────────────────────
def save_summary(all_results: list[dict]):
    """이번 실행 결과를 기존 CSV에 병합 저장. 같은 (model, fs, target)은 덮어씀."""
    path = RESULTS_DIR / "cv_scores" / "phase1_cv_summary.csv"

    if path.exists():
        existing = pd.read_csv(path)
    else:
        existing = pd.DataFrame()

    rows = []
    for r in all_results:
        row = {"model": r["model"], "fs": r["feature_set"], "target": r["target"]}
        for k, v in r["mean_metrics"].items():
            row[f"cv_{k}_mean"] = round(v, 4)
        for k, v in r["std_metrics"].items():
            row[f"cv_{k}_std"] = round(v, 4)
        rows.append(row)

    new_df = pd.DataFrame(rows)

    if not existing.empty and not new_df.empty:
        keys = ["model", "fs", "target"]
        mask = existing.set_index(keys).index.isin(new_df.set_index(keys).index)
        existing = existing[~mask]
        summary_df = pd.concat([existing, new_df], ignore_index=True)
    else:
        summary_df = new_df if not new_df.empty else existing

    summary_df.to_csv(path, index=False)
    logger.info("CV 요약 저장: %s (%d행)", path, len(summary_df))
    return summary_df


# ── 메인 ─────────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=str, default="all",
                        help="쉼표 구분 모델 이름 or 'all'")
    parser.add_argument("--targets", type=str, default="all",
                        help="쉼표 구분 타겟 이름 or 'all'")
    parser.add_argument("--no-test", action="store_true",
                        help="Hold-out test 평가 생략")
    parser.add_argument("--skip-existing", action="store_true",
                        help="이미 결과 파일 있는 실험은 건너뜀")
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info("데이터 로드...")
    df = load_feature_df()
    logger.info("전체 유효 화합물: %d", len(df))

    df_train, df_test = split_holdout(df)
    logger.info("Train: %d  Test: %d", len(df_train), len(df_test))

    fs_map_train = build_feature_sets(df_train)
    fs1_cols = fs_map_train["FS1"]
    logger.info("FS1: %d개 feature", len(fs1_cols))

    fs2_cols = get_or_compute_fs2(df_train, fs1_cols)
    fs_map_train["FS2"] = fs2_cols
    logger.info("FS2: %d개 feature", len(fs2_cols))

    targets = TARGETS if args.targets == "all" else [t.strip() for t in args.targets.split(",")]

    if args.models == "all":
        model_names = list(MODEL_FS_PLAN.keys())
    else:
        model_names = [m.strip() for m in args.models.split(",")]

    all_results = []
    test_summary = []

    for model_name in model_names:
        if model_name not in MODEL_FS_PLAN:
            logger.warning("알 수 없는 모델: %s — 건너뜀", model_name)
            continue

        for fs_name in MODEL_FS_PLAN[model_name]:
            if fs_name not in fs_map_train:
                logger.warning("FS 없음: %s — 건너뜀", fs_name)
                continue

            feature_cols = fs_map_train[fs_name]
            trainer = Trainer(df_train, feature_cols, results_dir=RESULTS_DIR)

            for target in targets:
                tag = f"{model_name}_{fs_name}_{target}"

                if args.skip_existing:
                    json_path = RESULTS_DIR / "cv_scores" / f"{tag}.json"
                    if json_path.exists():
                        logger.info("SKIP (기존 결과 존재): %s", tag)
                        with open(json_path) as f:
                            all_results.append(json.load(f))
                        continue

                logger.info("=== %s | %s | %s ===", model_name, fs_name, target)
                model = _build_model(model_name)
                model.fs = fs_name
                result = trainer.run(model, target)
                all_results.append(result)

    if not args.no_test:
        logger.info("Hold-out test 평가...")
        for model_name in model_names:
            if model_name not in MODEL_FS_PLAN:
                continue
            for fs_name in MODEL_FS_PLAN[model_name]:
                if fs_name not in fs_map_train:
                    continue

                feature_cols = fs_map_train[fs_name]
                is_graph = fs_name in ("FS4", "FS6")
                if is_graph:
                    X_tr = df_train[feature_cols].values          # dtype=object (SMILES)
                    X_te = df_test[feature_cols].values
                else:
                    X_tr = df_train[feature_cols].values.astype(float)
                    X_te = df_test[feature_cols].values.astype(float)

                for target in targets:
                    y_tr = df_train[target].values.astype(float)
                    y_te = df_test[target].values.astype(float)

                    model = _build_model(model_name)
                    model.fs = fs_name
                    model.fit(X_tr, y_tr)
                    y_pred = model.predict(X_te)

                    m = compute_metrics(y_te, y_pred, target)
                    m.update({"model": model_name, "target": target, "fs": fs_name})
                    test_summary.append(m)
                    logger.info("[TEST] %s|%s|%s — RMSE=%.4f  R²=%.4f  MAPE=%.2f%%",
                                model_name, fs_name, target, m["rmse"], m["r2"], m["mape"])

        test_path = RESULTS_DIR / "cv_scores" / "phase1_test_summary.csv"
        new_test_df = pd.DataFrame(test_summary)
        if test_path.exists():
            existing_test = pd.read_csv(test_path)
            keys = ["model", "fs", "target"]
            mask = existing_test.set_index(keys).index.isin(new_test_df.set_index(keys).index)
            existing_test = existing_test[~mask]
            test_df = pd.concat([existing_test, new_test_df], ignore_index=True)
        else:
            test_df = new_test_df
        test_df.to_csv(test_path, index=False)
        logger.info("Test 결과 저장: %s (%d행)", test_path, len(test_df))

    summary_df = save_summary(all_results)
    print("\n" + summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
