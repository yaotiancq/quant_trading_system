from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from numbers import Integral, Real
from typing import Protocol

import pandas as pd


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"
    HOLD = "HOLD"


class SignalType(str, Enum):
    RULE_BASED = "RULE_BASED"
    ML = "ML"
    COMBINED = "COMBINED"


@dataclass(frozen=True)
class SignalProvenance:
    source_name: str
    source_type: SignalType
    model_version: str | None = None
    feature_set: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "source_name": self.source_name,
            "source_type": self.source_type.value,
            "model_version": self.model_version,
            "feature_set": list(self.feature_set),
        }


@dataclass(frozen=True)
class TradingSignal:
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    direction: SignalDirection
    strength: float = 0.0
    confidence: float = 1.0
    target_position: float | None = None
    provenance: SignalProvenance | None = None
    confidence_metadata: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return _json_safe(
            {
                "timestamp": self.timestamp.isoformat(),
                "symbol": self.symbol,
                "signal_type": self.signal_type.value,
                "direction": self.direction.value,
                "strength": self.strength,
                "confidence": self.confidence,
                "target_position": self.target_position,
                "provenance": self.provenance.to_dict() if self.provenance else None,
                "confidence_metadata": self.confidence_metadata,
                "metadata": self.metadata,
            }
        )


class SignalProvider(Protocol):
    name: str

    def generate(self, history: pd.DataFrame, timestamp: pd.Timestamp) -> list[TradingSignal]:
        """Generate signals using market data available at or before timestamp."""


def _json_safe(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        return float(value)
    return value
