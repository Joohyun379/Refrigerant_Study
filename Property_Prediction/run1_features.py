"""
Feature 추출 파이프라인 실행 스크립트

실행 순서:
  1. run_pipeline.py  → data/processed/refrigerants_final.csv
  2. run_features.py  → data/processed/features_raw.csv, features_clean.csv  ← 여기
  3. run_phase1.py    → results/

실행 예시:
  python run1_features.py

  # 3D feature 포함 (느림)
  python run1_features.py --include-3d

  # 특정 화합물만 (디버깅용)
  python run1_features.py --identifier "R-134a"
"""
from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_features")

RAW_PATH       = ROOT / "data" / "processed" / "refrigerants_final.csv"
FEAT_RAW_PATH  = ROOT / "data" / "processed" / "features_raw.csv"
FEAT_CLEAN_PATH = ROOT / "data" / "processed" / "features_clean.csv"

# feature 추출 시 항상 제외할 컬럼 (NaN 비율 높음 또는 상수)
DROP_COLS = ["gc_joback_Tc_K", "gt_n_other"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-3d", action="store_true",
                        help="3D geometry feature(Cat4) 포함 (기본: 제외)")
    parser.add_argument("--identifier", type=str, default=None,
                        help="특정 화합물만 추출 (디버깅용)")
    parser.add_argument("--force", action="store_true",
                        help="캐시 무시하고 전체 재추출")
    return parser.parse_args()


def extract_features(df: pd.DataFrame, include_3d: bool) -> pd.DataFrame:
    from features.pipeline import FeaturePipeline

    pipe = FeaturePipeline(include_3d=include_3d, include_whim=False, use_xtb=False)

    smiles_list  = df["SMILES"].tolist()
    identifiers  = df["identifier"].tolist()

    logger.info("Feature 추출 시작: %d개 화합물 (3D=%s)", len(df), include_3d)
    feat_df = pipe.transform_batch(smiles_list, identifiers)

    # label, group 붙이기
    meta = df[["identifier", "label", "group"]].reset_index(drop=True)
    feat_df = feat_df.reset_index(drop=True)
    result = pd.merge(feat_df, meta, on="identifier", how="left")
    return result


def clean_features(feat_df: pd.DataFrame) -> pd.DataFrame:
    """
    NaN 처리:
      1. DROP_COLS 제거
      2. 나머지 NaN → 0 (비존재 구조를 0으로 표현)
    """
    # 존재하는 컬럼만 제거
    to_drop = [c for c in DROP_COLS if c in feat_df.columns]
    if to_drop:
        logger.info("제거 컬럼: %s", to_drop)
        feat_df = feat_df.drop(columns=to_drop)

    # NaN → 0 (컬럼별 개별 처리로 길이 불일치 방지)
    meta_cols = {"identifier", "label", "group"}
    num_cols = [c for c in feat_df.columns if c not in meta_cols]
    nan_counts = feat_df[num_cols].isna().sum()
    nan_cols = nan_counts[nan_counts > 0]
    if len(nan_cols):
        logger.info("NaN 컬럼 %d개 → 0으로 채움:", len(nan_cols))
        for col in nan_cols.index:
            feat_df[col] = feat_df[col].fillna(0)

    return feat_df


def main():
    args = parse_args()

    # ── 원본 데이터 로드 ──────────────────────────────────────────────────────
    if not RAW_PATH.exists():
        logger.error("원본 데이터 없음: %s\n먼저 run_pipeline.py를 실행하세요.", RAW_PATH)
        sys.exit(1)

    df = pd.read_csv(RAW_PATH)

    # valid 필터
    df = df[df["valid"].astype(str).str.lower() == "true"].reset_index(drop=True)
    logger.info("유효 화합물: %d개", len(df))

    # 특정 화합물만
    if args.identifier:
        df = df[df["identifier"] == args.identifier].reset_index(drop=True)
        if df.empty:
            logger.error("화합물 없음: %s", args.identifier)
            sys.exit(1)
        logger.info("단일 화합물 모드: %s", args.identifier)

    # ── features_raw.csv 캐시 확인 ────────────────────────────────────────────
    if FEAT_RAW_PATH.exists() and not args.force and args.identifier is None:
        logger.info("캐시 로드: %s", FEAT_RAW_PATH)
        feat_raw = pd.read_csv(FEAT_RAW_PATH)
    else:
        feat_raw = extract_features(df, include_3d=args.include_3d)
        if args.identifier is None:
            FEAT_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
            feat_raw.to_csv(FEAT_RAW_PATH, index=False)
            logger.info("features_raw.csv 저장: %s  (%d행 × %d열)",
                        FEAT_RAW_PATH, feat_raw.shape[0], feat_raw.shape[1])

    # ── 정제 및 features_clean.csv 저장 ──────────────────────────────────────
    feat_clean = clean_features(feat_raw.copy())

    if args.identifier is None:
        feat_clean.to_csv(FEAT_CLEAN_PATH, index=False)
        logger.info("features_clean.csv 저장: %s  (%d행 × %d열)",
                    FEAT_CLEAN_PATH, feat_clean.shape[0], feat_clean.shape[1])

    # ── 요약 출력 ─────────────────────────────────────────────────────────────
    meta_cols = {"identifier", "label", "group"}
    feat_cols = [c for c in feat_clean.columns if c not in meta_cols]
    nan_remaining = feat_clean[feat_cols].isna().sum().sum()

    logger.info("완료 — 특성 수: %d개, 잔여 NaN: %d", len(feat_cols), nan_remaining)
    print("\n=== Feature 요약 ===")
    for prefix, name in [("gc", "Cat1 Group Contribution"),
                          ("lg", "Cat2 Local Graph"),
                          ("gt", "Cat3 Global Topology"),
                          ("rd", "Cat4 3D Geometry"),
                          ("rf", "Cat5 Refrigerant-Specific"),
                          ("el", "Cat6 Electronic")]:
        cnt = sum(1 for c in feat_cols if c.startswith(prefix + "_"))
        if cnt:
            print(f"  {name:35s}: {cnt:4d}개")
    print(f"  {'합계':35s}: {len(feat_cols):4d}개")


if __name__ == "__main__":
    main()
