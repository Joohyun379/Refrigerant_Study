"""
Feature Set 정의

FS1: 전체 engineered features (gc + lg + gt + rf + el)
FS2: SHAP/importance 상위 N개 (Phase 1 GBM 결과로 결정 — 현재는 FS1 그대로)
FS3_*: 범주별 단독
"""
from __future__ import annotations
import pandas as pd
from experiments.configs.base import FEAT_PATH, META_COLS, TARGETS


def get_feature_cols(df: pd.DataFrame, prefix: str | None = None) -> list[str]:
    """
    df에서 feature 컬럼을 반환한다.
    prefix가 None이면 전체(FS1), 지정하면 해당 접두사만.
    """
    exclude = set(META_COLS + TARGETS)
    cols = [c for c in df.columns if c not in exclude]
    if prefix is not None:
        cols = [c for c in cols if c.startswith(prefix)]
    return cols


# ── 접두사 매핑 ────────────────────────────────────────────────────────────
PREFIX_MAP = {
    "FS3_gc": "gc_",
    "FS3_lg": "lg_",
    "FS3_gt": "gt_",
    "FS3_rf": "rf_",
    "FS3_el": "el_",
}


def load_feature_df() -> pd.DataFrame:
    """
    features_clean.csv + refrigerants_final.csv 합성.

    features_clean.csv에는 타겟 컬럼(Tc_K, Pc_MPa, omega)이 없으므로
    refrigerants_final.csv에서 merge한다.
    """
    from experiments.configs.base import RAW_PATH
    feat = pd.read_csv(FEAT_PATH)
    raw  = pd.read_csv(RAW_PATH, usecols=["identifier", "SMILES", "Tc_K", "Pc_MPa", "omega", "valid"])

    # valid 필터
    raw = raw[raw["valid"].astype(str).str.lower() == "true"][["identifier", "SMILES", "Tc_K", "Pc_MPa", "omega"]]

    df = feat.merge(raw, on="identifier", how="inner").reset_index(drop=True)
    return df


def build_feature_sets(df: pd.DataFrame) -> dict[str, list[str]]:
    """FS 이름 → feature 컬럼 리스트 딕셔너리 반환."""
    fs = {}
    fs["FS1"] = get_feature_cols(df)
    fs["FS2"] = fs["FS1"]   # placeholder: GBM 결과 후 갱신 예정
    for name, prefix in PREFIX_MAP.items():
        fs[name] = get_feature_cols(df, prefix=prefix)
    # FS4: GNN 전용 — SMILES 문자열 컬럼
    fs["FS4"] = ["SMILES"]
    # FS6: Pretrained LM 전용 — Raw SMILES 문자열
    fs["FS6"] = ["SMILES"]
    return fs
