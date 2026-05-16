from __future__ import annotations

import pandas as pd


def add_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    frames: list[pd.DataFrame] = []
    for symbol, frame in df.sort_values(["symbol", "timestamp"]).groupby("symbol", sort=False):
        item = frame.copy()
        item["return_1"] = item["close"].pct_change()
        item["return_5"] = item["close"].pct_change(5)
        item["ma_5"] = item["close"].rolling(5).mean()
        item["ma_20"] = item["close"].rolling(20).mean()
        item["ma_ratio_5_20"] = item["ma_5"] / item["ma_20"] - 1.0
        item["volatility_20"] = item["return_1"].rolling(20).std()
        item["volume_zscore_20"] = (item["volume"] - item["volume"].rolling(20).mean()) / item["volume"].rolling(20).std()
        item["intrabar_range"] = (item["high"] - item["low"]) / item["close"]
        item["symbol"] = symbol
        frames.append(item)
    return pd.concat(frames, ignore_index=True).sort_values(["timestamp", "symbol"]).reset_index(drop=True)


def build_feature_matrix(df: pd.DataFrame, feature_columns: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    columns = feature_columns or [
        "return_1",
        "return_5",
        "ma_ratio_5_20",
        "volatility_20",
        "volume_zscore_20",
        "intrabar_range",
    ]
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "symbol", *columns]), columns
    featured = add_basic_features(df)
    matrix = featured[["timestamp", "symbol", *columns]].dropna().reset_index(drop=True)
    return matrix, columns
