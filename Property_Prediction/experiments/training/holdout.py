"""
Hold-out test set 분리 (group 단위, Tc 층화)

사용 방법:
    df_train, df_test = split_holdout(df)
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from experiments.configs.base import TEST_SIZE, RANDOM_STATE, TC_BINS, TC_LABELS


def split_holdout(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    group 단위로 test_size 비율만큼 hold-out 분리.
    Tc_K 구간 층화로 test set 대표성 확보.

    Returns
    -------
    df_train, df_test
    """
    df = df.reset_index(drop=True)
    strata = pd.cut(
        df["Tc_K"],
        bins=TC_BINS,
        labels=TC_LABELS,
        right=True,
        include_lowest=True,
    ).astype(int).values

    groups = df["group"].values

    n_splits = max(2, round(1 / TEST_SIZE))   # TEST_SIZE=0.20 → n_splits=5
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)

    # 첫 번째 fold의 val을 test set으로 사용
    train_idx, test_idx = next(sgkf.split(X=df, y=strata, groups=groups))
    return df.iloc[train_idx].reset_index(drop=True), df.iloc[test_idx].reset_index(drop=True)
