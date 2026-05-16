from __future__ import annotations

from collections import defaultdict

from qts.signals.base import SignalDirection, SignalType, TradingSignal


class WeightedSignalCombiner:
    name = "weighted_signal_combiner"

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or {}

    def combine(self, signals: list[TradingSignal]) -> list[TradingSignal]:
        scores: dict[tuple[object, str], float] = defaultdict(float)
        confidences: dict[tuple[object, str], list[float]] = defaultdict(list)
        for signal in signals:
            provider = str(signal.metadata.get("provider", "default"))
            weight = self.weights.get(provider, 1.0)
            signed = _signed_direction(signal.direction) * signal.strength * signal.confidence
            scores[(signal.timestamp, signal.symbol)] += weight * signed
            confidences[(signal.timestamp, signal.symbol)].append(signal.confidence)

        combined: list[TradingSignal] = []
        for (timestamp, symbol), score in scores.items():
            direction = SignalDirection.LONG if score > 0 else SignalDirection.SHORT if score < 0 else SignalDirection.FLAT
            combined.append(
                TradingSignal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.COMBINED,
                    direction=direction,
                    strength=min(abs(score), 1.0),
                    confidence=sum(confidences[(timestamp, symbol)]) / len(confidences[(timestamp, symbol)]),
                    target_position=max(min(score, 1.0), -1.0),
                    metadata={"provider": self.name},
                )
            )
        return combined


def _signed_direction(direction: SignalDirection) -> int:
    if direction == SignalDirection.LONG:
        return 1
    if direction == SignalDirection.SHORT:
        return -1
    return 0
