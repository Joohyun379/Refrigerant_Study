"""
수집 데이터 품질 검증
- 필수 컬럼 존재 여부
- 물성값 합리적 범위 확인
- 결측률 리포트
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)

# 냉매 물성의 합리적 범위 (경험적 기준)
VALID_RANGES = {
    "Tc_K":    (100.0, 1000.0),   # 임계온도 [K]
    "Pc_MPa":  (0.01,  100.0),    # 임계압력 [MPa]
    "omega":   (-0.5,  2.0),      # 이심인자 [-]
    "MolecularWeight": (10, 2000),
}


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """
    각 행의 유효성을 검사하여 'valid' 컬럼 추가
    문제가 있는 행은 'validation_notes' 컬럼에 상세 내용 기재
    """
    df = df.copy()
    notes = []
    valid_flags = []

    for _, row in df.iterrows():
        row_notes = []

        for col, (lo, hi) in VALID_RANGES.items():
            if col not in df.columns:
                continue
            val = row.get(col)
            if pd.isna(val):
                row_notes.append(f"{col}=missing")
            elif not (lo <= float(val) <= hi):
                row_notes.append(f"{col}={val} out of range [{lo}, {hi}]")

        notes.append("; ".join(row_notes) if row_notes else "OK")
        valid_flags.append(len(row_notes) == 0)

    df["valid"] = valid_flags
    df["validation_notes"] = notes
    return df


def report(df: pd.DataFrame) -> None:
    """결측률 및 유효 비율 출력"""
    total = len(df)
    print(f"\n{'='*50}")
    print(f"총 화합물 수: {total}")
    print(f"유효 데이터:  {df['valid'].sum()} / {total}")
    print(f"\n--- 컬럼별 결측률 ---")

    check_cols = ["cid", "CanonicalSMILES", "MolecularFormula",
                  "Tc_K", "Pc_MPa", "omega"]
    for col in check_cols:
        if col in df.columns:
            missing = df[col].isna().sum()
            print(f"  {col:25s}: {missing:3d} missing ({100*missing/total:.1f}%)")

    print(f"{'='*50}\n")


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/refrigerants_normalized.csv"
    df = pd.read_csv(path)
    df = validate(df)
    report(df)
    print(df[["identifier", "Tc_K", "Pc_MPa", "omega", "valid", "validation_notes"]].to_string())
