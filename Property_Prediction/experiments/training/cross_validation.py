"""
Group-stratified K-Fold CV

규칙:
  1. 같은 group은 반드시 같은 fold (train 또는 val)에만 속함 → 데이터 누수 방지
  2. Tc_K 구간(TC_BINS)을 기준으로 fold 간 분포가 고르도록 층화 샘플링
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from experiments.configs.base import N_SPLITS, RANDOM_STATE, TC_BINS, TC_LABELS


def make_tc_strata(tc_series: pd.Series) -> np.ndarray:
    """Tc_K 값을 구간 레이블로 변환."""
    return pd.cut(
        tc_series,
        bins=TC_BINS,
        labels=TC_LABELS,
        right=True,
        include_lowest=True,
    ).astype(int).values


def get_cv_splits(
    df: pd.DataFrame,
    n_splits: int = N_SPLITS,
    random_state: int = RANDOM_STATE,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """
    Parameters
    ----------
    df : 전체 학습 데이터프레임 (index가 0-based int이어야 함)
        필수 컬럼: group, Tc_K

    Returns
    -------
    splits : [(train_idx, val_idx), ...] — df.iloc 기준 정수 인덱스
    """
    groups = df["group"].values
    strata = make_tc_strata(df["Tc_K"])

    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    splits = list(sgkf.split(X=df, y=strata, groups=groups))
    return splits
