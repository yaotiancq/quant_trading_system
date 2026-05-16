from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class BaselineModel:
    def __init__(self, feature_columns: list[str], model: Pipeline | None = None, model_version: str = "baseline_logistic_v1") -> None:
        self.feature_columns = feature_columns
        self.model_version = model_version
        self.model = model or Pipeline(
            [
                ("scaler", StandardScaler()),
                ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
            ]
        )

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "BaselineModel":
        self.model.fit(X[self.feature_columns], y)
        return self

    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        probability = self.model.predict_proba(X[self.feature_columns])[:, 1]
        return pd.Series(probability, index=X.index)

    def score(self, X: pd.DataFrame, y: pd.Series) -> float:
        predictions = (self.predict_proba(X) >= 0.5).astype(int)
        return float(accuracy_score(y, predictions))

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"feature_columns": self.feature_columns, "model": self.model, "model_version": self.model_version}, output)
        return output

    @classmethod
    def load(cls, path: str | Path) -> "BaselineModel":
        payload = joblib.load(path)
        return cls(
            feature_columns=payload["feature_columns"],
            model=payload["model"],
            model_version=payload.get("model_version", "baseline_logistic_v1"),
        )
