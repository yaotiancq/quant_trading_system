from __future__ import annotations

from datetime import datetime

import pandas as pd

from qts.config.loader import EnvSettings
from qts.data.validation import normalize_market_data


class AlpacaHistoricalDataClient:
    def __init__(self, settings: EnvSettings, feed: str = "iex") -> None:
        if not settings.alpaca_api_key_id or not settings.alpaca_api_secret_key:
            raise ValueError("Alpaca API credentials are required in environment variables.")
        from alpaca.data.historical import StockHistoricalDataClient

        self.client = StockHistoricalDataClient(settings.alpaca_api_key_id, settings.alpaca_api_secret_key)
        self.feed = feed

    def get_stock_bars(self, symbols: list[str], timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
        from alpaca.data.requests import StockBarsRequest

        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=_to_alpaca_timeframe(timeframe),
            start=start,
            end=end,
            feed=self.feed,
        )
        raw = self.client.get_stock_bars(request).df.reset_index()
        if "level_0" in raw.columns:
            raw = raw.rename(columns={"level_0": "symbol", "level_1": "timestamp"})
        return normalize_market_data(raw, timeframe=timeframe, source="alpaca", timezone="UTC")


def _to_alpaca_timeframe(value: str):
    from alpaca.data.timeframe import TimeFrame

    if value == "1Sec":
        raise ValueError(
            "The installed Alpaca stock bars SDK does not expose second bars. "
            "Use local normalized second bars or add a trade/quote aggregation adapter."
        )
    mapping = {
        "1Min": TimeFrame.Minute,
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day,
    }
    if value not in mapping:
        raise ValueError(f"Unsupported Alpaca timeframe: {value}")
    return mapping[value]
