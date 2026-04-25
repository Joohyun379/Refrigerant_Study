"""
실험 공통 설정
"""
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

# ── 경로 ────────────────────────────────────────────────────────────────────
DATA_DIR    = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "results"
FEAT_PATH   = DATA_DIR / "features_clean.csv"
RAW_PATH    = DATA_DIR / "refrigerants_final.csv"

# ── 타겟 변수 ────────────────────────────────────────────────────────────────
TARGETS = ["Tc_K", "Pc_MPa", "omega"]

# Tc 구간 정의 (데이터 분할 층화용)
TC_BINS   = [0, 200, 350, 500, 700, float("inf")]
TC_LABELS = [0, 1, 2, 3, 4]

# 각 타겟의 값 범위 (Normalized RMSE 계산용)
TARGET_RANGES = {
    "Tc_K":   874.0,   # max - min
    "Pc_MPa":  21.2,
    "omega":    1.48,
}

# ── CV 설정 ──────────────────────────────────────────────────────────────────
N_SPLITS     = 5
RANDOM_STATE = 42
TEST_SIZE    = 0.20    # hold-out test set 비율

# ── 메타 컬럼 (feature 제외) ──────────────────────────────────────────────────
META_COLS = ["identifier", "label", "group", "SMILES"]
