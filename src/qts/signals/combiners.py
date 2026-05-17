from __future__ import annotations

from collections import defaultdict
from typing import Literal

from qts.signals.base import SignalDirection, SignalType, TradingSignal


class WeightedSignalCombiner:
    name = "weighted_signal_combiner"

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        method: Literal["equal_weight", "confidence_weighted"] = "confidence_weighted",
        conflict_policy: Literal["flat", "hold"] = "flat",
        deadband: float = 1e-9,
    ) -> None:
        self.weights = weights or {}
        self.method = method
        self.conflict_policy = conflict_policy
        self.deadband = deadband

    def combine(self, signals: list[TradingSignal]) -> list[TradingSignal]:
        scores: dict[tuple[object, str], float] = defaultdict(float)
        total_weights: dict[tuple[object, str], float] = defaultdict(float)
        confidences: dict[tuple[object, str], list[float]] = defaultdict(list)
        counts: dict[tuple[object, str], int] = defaultdict(int)
        directions: dict[tuple[object, str], set[SignalDirection]] = defaultdict(set)
        for signal in signals:
            key = (signal.timestamp, signal.symbol)
            provider = str(signal.metadata.get("provider", "default"))
            weight = self.weights.get(provider, 1.0)
            confidence = signal.confidence if self.method == "confidence_weighted" else 1.0
            signed = _signed_direction(signal.direction) * max(signal.strength, 1.0 if signal.direction in {SignalDirection.LONG, SignalDirection.SHORT} else 0.0)
            scores[key] += weight * signed * confidence
            total_weights[key] += abs(weight * confidence)
            confidences[key].append(signal.confidence)
            counts[key] += 1
            directions[key].add(signal.direction)

        combined: list[TradingSignal] = []
        for (timestamp, symbol), score in scores.items():
            normalized_score = score / total_weights[(timestamp, symbol)] if total_weights[(timestamp, symbol)] else 0.0
            has_long = SignalDirection.LONG in directions[(timestamp, symbol)]
            has_short = SignalDirection.SHORT in directions[(timestamp, symbol)]
            conflict = has_long and has_short and abs(normalized_score) <= self.deadband
            if conflict and self.conflict_policy == "hold":
                direction = SignalDirection.HOLD
            elif conflict:
                direction = SignalDirection.FLAT
            else:
                direction = SignalDirection.LONG if normalized_score > self.deadband else SignalDirection.SHORT if normalized_score < -self.deadband else SignalDirection.FLAT
            combined.append(
                TradingSignal(
                    timestamp=timestamp,
                    symbol=symbol,
                    signal_type=SignalType.COMBINED,
                    direction=direction,
                    strength=min(abs(normalized_score), 1.0),
                    confidence=sum(confidences[(timestamp, symbol)]) / len(confidences[(timestamp, symbol)]),
                    target_position=0.0 if direction in {SignalDirection.FLAT, SignalDirection.HOLD} else max(min(normalized_score, 1.0), -1.0),
                    metadata={
                        "provider": self.name,
                        "method": self.method,
                        "conflict": conflict,
                        "input_count": counts[(timestamp, symbol)],
                    },
                )
            )
        return combined


def _signed_direction(direction: SignalDirection) -> int:
    if direction == SignalDirection.LONG:
        return 1
    if direction == SignalDirection.SHORT:
        return -1
    return 0
