from __future__ import annotations

import pandas as pd

from qts.features.technical import build_feature_matrix


def build_supervised_dataset(
    bars: pd.DataFrame,
    horizon: int = 1,
    threshold: float = 0.0,
) -> tuple[pd.DataFrame, pd.Series, list[str], pd.DataFrame]:
    if horizon < 1:
        raise ValueError("horizon must be at least 1.")
    features, feature_columns = build_feature_matrix(bars)
    labels = []
    for symbol, frame in bars.sort_values(["symbol", "timestamp"]).groupby("symbol", sort=False):
        future_return = frame["close"].shift(-horizon) / frame["close"] - 1.0
        label_frame = frame[["timestamp", "symbol"]].copy()
        label_frame["label"] = (future_return > threshold).astype(int)
        label_frame = label_frame.iloc[:-horizon]
        labels.append(label_frame)
    if not labels:
        raise ValueError("bars must contain at least one symbol.")
    label_data = pd.concat(labels, ignore_index=True)
    dataset = features.merge(label_data, on=["timestamp", "symbol"], how="inner").dropna().sort_values(["timestamp", "symbol"])
    y = dataset["label"].astype(int)
    X = dataset[feature_columns]
    metadata = dataset[["timestamp", "symbol"]].reset_index(drop=True)
    return X.reset_index(drop=True), y.reset_index(drop=True), feature_columns, metadata


def time_train_test_split(
    X: pd.DataFrame,
    y: pd.Series,
    metadata: pd.DataFrame,
    train_fraction: float = 0.7,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, pd.DataFrame]:
    if not 0.0 < train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0 and 1.")
    ordered = metadata.sort_values(["timestamp", "symbol"]).index
    cutoff = int(len(ordered) * train_fraction)
    train_idx = ordered[:cutoff]
    test_idx = ordered[cutoff:]
    return (
        X.loc[train_idx].reset_index(drop=True),
        X.loc[test_idx].reset_index(drop=True),
        y.loc[train_idx].reset_index(drop=True),
        y.loc[test_idx].reset_index(drop=True),
        metadata.loc[train_idx].reset_index(drop=True),
        metadata.loc[test_idx].reset_index(drop=True),
    )
