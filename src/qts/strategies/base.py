from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

import pandas as pd

from qts.backtest.orders import OrderRequest


@dataclass(frozen=True)
class TargetPosition:
    timestamp: datetime
    symbol: str
    target_fraction: float
    metadata: dict[str, object] = field(default_factory=dict)


class Strategy(Protocol):
    name: str

    def generate_orders(self, history: pd.DataFrame, timestamp: pd.Timestamp, broker: object) -> list[OrderRequest]:
        """Return broker-neutral order requests using data available through timestamp."""
