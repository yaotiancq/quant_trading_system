from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

import pandas as pd


@dataclass(frozen=True)
class TargetPosition:
    timestamp: datetime
    symbol: str
    target_fraction: float
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class OrderRequest:
    timestamp: datetime
    symbol: str
    side: str
    quantity: float
    order_type: Literal["market", "limit", "stop", "stop_limit", "trailing_stop"] = "market"
    time_in_force: Literal["day", "gtc", "opg", "cls", "ioc", "fok"] = "day"
    limit_price: float | None = None
    stop_price: float | None = None
    trail_price: float | None = None
    trail_percent: float | None = None
    extended_hours: bool = False
    order_class: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class Strategy(Protocol):
    name: str

    def generate_targets(self, history: pd.DataFrame, timestamp: pd.Timestamp) -> list[TargetPosition]:
        """Return desired portfolio target fractions using data available through timestamp."""
