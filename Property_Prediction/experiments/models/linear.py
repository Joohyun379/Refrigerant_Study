"""
선형 / 커널 / 가우시안 프로세스 회귀 모델
  - Ridge
  - Lasso
  - SVR (linear kernel)
  - SVR (RBF kernel)
  - GaussianProcessRegressor
"""
from __future__ import annotations
import numpy as np
from sklearn.linear_model import Ridge, Lasso
from sklearn.svm import SVR
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .base import BaseRegressor


def _scaled_pipeline(estimator) -> Pipeline:
    return Pipeline([("scaler", StandardScaler()), ("model", estimator)])


class RidgeRegressor(BaseRegressor):
    name = "Ridge"

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self._pipe = _scaled_pipeline(Ridge(alpha=alpha))

    def fit(self, X, y):
        self._pipe.fit(X, y)
        return self

    def predict(self, X):
        return self._pipe.predict(X)

    def get_params(self):
        return {"alpha": self.alpha}


class LassoRegressor(BaseRegressor):
    name = "Lasso"

    def __init__(self, alpha: float = 0.01, max_iter: int = 5000):
        self.alpha = alpha
        self.max_iter = max_iter
        self._pipe = _scaled_pipeline(Lasso(alpha=alpha, max_iter=max_iter))

    def fit(self, X, y):
        self._pipe.fit(X, y)
        return self

    def predict(self, X):
        return self._pipe.predict(X)

    def get_params(self):
        return {"alpha": self.alpha}


class SVRLinear(BaseRegressor):
    name = "SVR_Linear"

    def __init__(self, C: float = 1.0, epsilon: float = 0.1):
        self.C = C
        self.epsilon = epsilon
        self._pipe = _scaled_pipeline(SVR(kernel="linear", C=C, epsilon=epsilon))

    def fit(self, X, y):
        self._pipe.fit(X, y)
        return self

    def predict(self, X):
        return self._pipe.predict(X)

    def get_params(self):
        return {"C": self.C, "epsilon": self.epsilon}


class SVRRBF(BaseRegressor):
    name = "SVR_RBF"

    def __init__(self, C: float = 10.0, gamma: str = "scale", epsilon: float = 0.1):
        self.C = C
        self.gamma = gamma
        self.epsilon = epsilon
        self._pipe = _scaled_pipeline(SVR(kernel="rbf", C=C, gamma=gamma, epsilon=epsilon))

    def fit(self, X, y):
        self._pipe.fit(X, y)
        return self

    def predict(self, X):
        return self._pipe.predict(X)

    def get_params(self):
        return {"C": self.C, "gamma": self.gamma, "epsilon": self.epsilon}


class GPRegressor(BaseRegressor):
    name = "GP"

    def __init__(self, n_restarts: int = 3, random_state: int = 42):
        self.n_restarts = n_restarts
        self.random_state = random_state
        kernel = ConstantKernel(1.0) * RBF(1.0) + WhiteKernel(1e-2)
        self._scaler = StandardScaler()
        self._model = GaussianProcessRegressor(
            kernel=kernel,
            n_restarts_optimizer=n_restarts,
            random_state=random_state,
            normalize_y=True,
        )

    def fit(self, X, y):
        X_s = self._scaler.fit_transform(X)
        self._model.fit(X_s, y)
        return self

    def predict(self, X):
        X_s = self._scaler.transform(X)
        return self._model.predict(X_s)

    def get_params(self):
        return {"n_restarts": self.n_restarts}
