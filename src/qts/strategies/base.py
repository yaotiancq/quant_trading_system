from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

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
    order_type: str = "market"
    time_in_force: str = "day"
    metadata: dict[str, object] = field(default_factory=dict)


class Strategy(Protocol):
    name: str

    def generate_targets(self, history: pd.DataFrame, timestamp: pd.Timestamp) -> list[TargetPosition]:
        """Return desired portfolio target fractions using data available through timestamp."""

