from __future__ import annotations

from pathlib import Path

from qts.config.models import DataConfig
from qts.data.loader import load_market_data
from qts.ml.dataset import build_supervised_dataset, time_train_test_split
from qts.ml.model import BaselineModel


def train_baseline_model(
    data_config: DataConfig,
    output_path: str | Path,
    horizon: int = 1,
    threshold: float = 0.0,
    train_fraction: float = 0.7,
) -> BaselineModel:
    bars = load_market_data(data_config)
    X, y, feature_columns, metadata = build_supervised_dataset(bars, horizon=horizon, threshold=threshold)
    X_train, _, y_train, _, _, _ = time_train_test_split(X, y, metadata, train_fraction=train_fraction)
    model = BaselineModel(feature_columns).fit(X_train, y_train)
    model.save(output_path)
    return model


__all__ = ["train_baseline_model"]
