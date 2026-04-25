"""
트리 기반 앙상블 + sklearn MLP 모델
  - RandomForest
  - XGBoost
  - LightGBM
  - CatBoost
  - MLP (sklearn)
"""
from __future__ import annotations
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from .base import BaseRegressor


class RFRegressor(BaseRegressor):
    name = "RandomForest"

    def __init__(self, n_estimators: int = 300, max_features: float = 0.33,
                 min_samples_leaf: int = 2, random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_features = max_features
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self._model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_features=max_features,
            min_samples_leaf=min_samples_leaf,
            n_jobs=-1,
            random_state=random_state,
        )

    def fit(self, X, y):
        self._model.fit(X, y)
        return self

    def predict(self, X):
        return self._model.predict(X)

    def get_params(self):
        return {
            "n_estimators": self.n_estimators,
            "max_features": self.max_features,
            "min_samples_leaf": self.min_samples_leaf,
        }


class XGBRegressor(BaseRegressor):
    name = "XGBoost"

    def __init__(self, n_estimators: int = 500, learning_rate: float = 0.05,
                 max_depth: int = 6, subsample: float = 0.8,
                 colsample_bytree: float = 0.8, random_state: int = 42):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state = random_state

    def _build(self):
        from xgboost import XGBRegressor as _XGB
        return _XGB(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state,
            n_jobs=-1,
            verbosity=0,
        )

    def fit(self, X, y):
        self._model = self._build()
        self._model.fit(X, y)
        return self

    def predict(self, X):
        return self._model.predict(X)

    def get_params(self):
        return {
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "max_depth": self.max_depth,
        }


class LGBRegressor(BaseRegressor):
    name = "LightGBM"

    def __init__(self, n_estimators: int = 500, learning_rate: float = 0.05,
                 num_leaves: int = 63, min_child_samples: int = 5,
                 subsample: float = 0.8, colsample_bytree: float = 0.8,
                 random_state: int = 42):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state = random_state

    def _build(self):
        from lightgbm import LGBMRegressor as _LGB
        return _LGB(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            min_child_samples=self.min_child_samples,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state,
            n_jobs=-1,
            verbose=-1,
        )

    def fit(self, X, y):
        self._model = self._build()
        self._model.fit(X, y)
        return self

    def predict(self, X):
        return self._model.predict(X)

    def get_params(self):
        return {
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
        }


class CatBoostRegressor_(BaseRegressor):
    name = "CatBoost"

    def __init__(self, iterations: int = 500, learning_rate: float = 0.05,
                 depth: int = 6, random_state: int = 42):
        self.iterations = iterations
        self.learning_rate = learning_rate
        self.depth = depth
        self.random_state = random_state

    def _build(self):
        from catboost import CatBoostRegressor as _CB
        return _CB(
            iterations=self.iterations,
            learning_rate=self.learning_rate,
            depth=self.depth,
            random_seed=self.random_state,
            verbose=0,
        )

    def fit(self, X, y):
        self._model = self._build()
        self._model.fit(X, y)
        return self

    def predict(self, X):
        return self._model.predict(X)

    def get_params(self):
        return {
            "iterations": self.iterations,
            "learning_rate": self.learning_rate,
            "depth": self.depth,
        }


class MLPRegressorModel(BaseRegressor):
    name = "MLP_sklearn"

    def __init__(self, hidden_layer_sizes: tuple = (256, 128, 64),
                 max_iter: int = 1000, random_state: int = 42):
        self.hidden_layer_sizes = hidden_layer_sizes
        self.max_iter = max_iter
        self.random_state = random_state
        self._scaler = StandardScaler()
        self._model = MLPRegressor(
            hidden_layer_sizes=hidden_layer_sizes,
            activation="relu",
            solver="adam",
            early_stopping=True,
            validation_fraction=0.1,
            max_iter=max_iter,
            random_state=random_state,
        )

    def fit(self, X, y):
        X_s = self._scaler.fit_transform(X)
        self._model.fit(X_s, y)
        return self

    def predict(self, X):
        X_s = self._scaler.transform(X)
        return self._model.predict(X_s)

    def get_params(self):
        return {
            "hidden_layer_sizes": self.hidden_layer_sizes,
            "max_iter": self.max_iter,
        }
