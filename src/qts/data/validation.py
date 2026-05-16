from __future__ import annotations

import pandas as pd

from qts.data.models import MARKET_DATA_COLUMNS


def normalize_market_data(
    df: pd.DataFrame,
    timeframe: str = "1Min",
    source: str = "local",
    timezone: str = "UTC",
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=MARKET_DATA_COLUMNS)

    result = df.copy()
    result.columns = [str(col).lower() for col in result.columns]
    if "time" in result.columns and "timestamp" not in result.columns:
        result = result.rename(columns={"time": "timestamp"})
    if "symbol" not in result.columns:
        raise ValueError("Market data must include a symbol column.")
    if "timestamp" not in result.columns:
        raise ValueError("Market data must include a timestamp column.")

    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True).dt.tz_convert(timezone)
    for column in ["open", "high", "low", "close", "volume"]:
        if column not in result.columns:
            raise ValueError(f"Market data must include {column}.")
        result[column] = pd.to_numeric(result[column], errors="coerce")

    result["trade_count"] = pd.to_numeric(result.get("trade_count"), errors="coerce") if "trade_count" in result else pd.NA
    result["vwap"] = pd.to_numeric(result.get("vwap"), errors="coerce") if "vwap" in result else pd.NA
    result["timeframe"] = result.get("timeframe", timeframe)
    result["source"] = result.get("source", source)
    result = result.dropna(subset=["timestamp", "symbol", "open", "high", "low", "close", "volume"])
    result = result[MARKET_DATA_COLUMNS].sort_values(["timestamp", "symbol"]).reset_index(drop=True)
    return result


def parse_timestamp_bound(value: str, timezone: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize(timezone)
    return timestamp.tz_convert(timezone)
