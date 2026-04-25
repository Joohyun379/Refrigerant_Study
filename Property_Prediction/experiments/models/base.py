"""
모델 추상 기반 클래스
"""
from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np


class BaseRegressor(ABC):
    """단일 타겟 회귀 모델의 공통 인터페이스."""

    # 서브클래스에서 설정
    name: str = "base"

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaseRegressor":
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        ...

    def get_params(self) -> dict:
        """하이퍼파라미터 딕셔너리 반환 (결과 저장용)."""
        return {}
