from __future__ import annotations

import pandas as pd

from qts.features.technical import build_feature_matrix
from qts.ml.model import BaselineModel
from qts.signals.base import SignalDirection, SignalProvenance, SignalType, TradingSignal


class MLSignalProvider:
    name = "baseline_ml"

    def __init__(
        self,
        model: BaselineModel,
        long_threshold: float = 0.55,
        short_threshold: float = 0.45,
        target_notional_fraction: float = 1.0,
        model_version: str | None = None,
        feature_set: list[str] | None = None,
    ) -> None:
        if not 0.0 <= short_threshold <= long_threshold <= 1.0:
            raise ValueError("Thresholds must satisfy 0 <= short_threshold <= long_threshold <= 1.")
        if not 0.0 <= target_notional_fraction <= 1.0:
            raise ValueError("target_notional_fraction must be between 0 and 1.")
        self.model = model
        self.long_threshold = long_threshold
        self.short_threshold = short_threshold
        self.target_notional_fraction = target_notional_fraction
        self.model_version = model_version or model.model_version
        self.feature_set = tuple(feature_set or model.feature_columns)

    def generate(self, history: pd.DataFrame, timestamp: pd.Timestamp) -> list[TradingSignal]:
        available = history[history["timestamp"] <= timestamp]
        matrix, feature_columns = build_feature_matrix(available)
        current = matrix[matrix["timestamp"] == timestamp]
        if current.empty:
            return [
                TradingSignal(
                    timestamp=timestamp.to_pydatetime(),
                    symbol=symbol,
                    signal_type=SignalType.ML,
                    direction=SignalDirection.HOLD,
                    provenance=SignalProvenance(
                        source_name=self.name,
                        source_type=SignalType.ML,
                        model_version=self.model_version,
                        feature_set=self.feature_set,
                    ),
                    confidence_metadata={
                        "method": "model_probability",
                        "reason": "insufficient_features",
                        "long_threshold": self.long_threshold,
                        "short_threshold": self.short_threshold,
                    },
                    metadata={"provider": self.name, "reason": "insufficient_features"},
                )
                for symbol in sorted(available["symbol"].unique())
            ]
        predictions = self.model.predict_proba(current)
        signals: list[TradingSignal] = []
        for row_index, row in current.iterrows():
            probability = float(predictions.loc[row_index])
            direction = (
                SignalDirection.LONG
                if probability >= self.long_threshold
                else SignalDirection.SHORT
                if probability <= self.short_threshold
                else SignalDirection.FLAT
            )
            signed_target = 1.0 if direction == SignalDirection.LONG else -1.0 if direction == SignalDirection.SHORT else 0.0
            signals.append(
                TradingSignal(
                    timestamp=timestamp.to_pydatetime(),
                    symbol=row["symbol"],
                    signal_type=SignalType.ML,
                    direction=direction,
                    strength=abs(probability - 0.5) * 2.0,
                    confidence=max(probability, 1.0 - probability),
                    target_position=signed_target * self.target_notional_fraction,
                    provenance=SignalProvenance(
                        source_name=self.name,
                        source_type=SignalType.ML,
                        model_version=self.model_version,
                        feature_set=tuple(feature_columns),
                    ),
                    confidence_metadata={
                        "method": "model_probability",
                        "probability_up": probability,
                        "long_threshold": self.long_threshold,
                        "short_threshold": self.short_threshold,
                    },
                    metadata={"provider": self.name, "probability_up": probability},
                )
            )
        return signals
