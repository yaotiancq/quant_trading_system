from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

MARKET_DATA_COLUMNS = [
    "timestamp",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trade_count",
    "vwap",
    "timeframe",
    "source",
]


@dataclass(frozen=True)
class MarketBar:
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: float | None = None
    vwap: float | None = None
    timeframe: str = "1Min"
    source: str = "local"

