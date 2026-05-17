from __future__ import annotations

import numpy as np
import pandas as pd


DEFAULT_FEATURE_COLUMNS = [
    "return_1",
    "return_5",
    "log_return_1",
    "ma_ratio_5_20",
    "volatility_20",
    "rsi_14",
    "vwap_deviation",
    "volume_zscore_20",
    "volume_ratio_5_20",
    "momentum_5",
    "momentum_10",
    "intrabar_range",
]


def add_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    frames: list[pd.DataFrame] = []
    for symbol, frame in df.sort_values(["symbol", "timestamp"]).groupby("symbol", sort=False):
        item = frame.copy()
        close = pd.to_numeric(item["close"], errors="coerce")
        high = pd.to_numeric(item["high"], errors="coerce")
        low = pd.to_numeric(item["low"], errors="coerce")
        volume = pd.to_numeric(item["volume"], errors="coerce")

        item["return_1"] = close.pct_change()
        item["return_5"] = close.pct_change(5)
        item["log_return_1"] = np.log(close / close.shift(1))
        item["ma_5"] = close.rolling(5).mean()
        item["ma_10"] = close.rolling(10).mean()
        item["ma_20"] = close.rolling(20).mean()
        item["ma_ratio_5_20"] = item["ma_5"] / item["ma_20"] - 1.0
        item["volatility_20"] = item["return_1"].rolling(20).std()
        item["rsi_14"] = calculate_rsi(close, window=14)

        typical_price = (high + low + close) / 3.0
        if "vwap" in item and item["vwap"].notna().any():
            vwap = pd.to_numeric(item["vwap"], errors="coerce")
        else:
            vwap = rolling_vwap(typical_price, volume)
        item["vwap_deviation"] = close / vwap.replace(0, pd.NA) - 1.0

        volume_mean_5 = volume.rolling(5).mean()
        volume_mean_20 = volume.rolling(20).mean()
        volume_std_20 = volume.rolling(20).std()
        item["volume_mean_20"] = volume_mean_20
        item["volume_zscore_20"] = (volume - volume_mean_20) / volume_std_20.replace(0, pd.NA)
        item["volume_ratio_5_20"] = volume_mean_5 / volume_mean_20.replace(0, pd.NA) - 1.0
        item["momentum_3"] = close / close.shift(3) - 1.0
        item["momentum_5"] = close / close.shift(5) - 1.0
        item["momentum_10"] = close / close.shift(10) - 1.0
        item["intrabar_range"] = (high - low) / close.replace(0, pd.NA)
        item["symbol"] = symbol
        frames.append(item)
    return pd.concat(frames, ignore_index=True).sort_values(["timestamp", "symbol"]).reset_index(drop=True)


def build_feature_matrix(df: pd.DataFrame, feature_columns: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    columns = feature_columns or DEFAULT_FEATURE_COLUMNS
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "symbol", *columns]), columns
    featured = add_basic_features(df)
    matrix = featured[["timestamp", "symbol", *columns]].dropna().reset_index(drop=True)
    return matrix, columns


def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.rolling(window).mean()
    avg_loss = losses.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    rsi = rsi.mask((avg_gain == 0) & (avg_loss > 0), 0.0)
    rsi = rsi.mask((avg_gain == 0) & (avg_loss == 0), 50.0)
    return rsi


def rolling_vwap(typical_price: pd.Series, volume: pd.Series, window: int = 20) -> pd.Series:
    safe_volume = volume.replace(0, pd.NA)
    return (typical_price * safe_volume).rolling(window).sum() / safe_volume.rolling(window).sum()
