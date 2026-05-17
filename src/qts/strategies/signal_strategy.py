from __future__ import annotations

import pandas as pd

from qts.config.models import StrategyConfig
from qts.ml.model import BaselineModel
from qts.ml.signal_provider import MLSignalProvider
from qts.signals.base import SignalDirection, SignalProvider
from qts.signals.rule_based import BreakoutSignal, MovingAverageCrossoverSignal, RsiMeanReversionSignal
from qts.strategies.base import TargetPosition


class SignalDrivenStrategy:
    def __init__(self, name: str, signal_provider: SignalProvider) -> None:
        self.name = name
        self.signal_provider = signal_provider

    def generate_targets(self, history: pd.DataFrame, timestamp: pd.Timestamp) -> list[TargetPosition]:
        targets: list[TargetPosition] = []
        for signal in self.signal_provider.generate(history, timestamp):
            if signal.direction == SignalDirection.HOLD:
                continue
            target = signal.target_position
            if target is None:
                target = 1.0 if signal.direction == SignalDirection.LONG else -1.0 if signal.direction == SignalDirection.SHORT else 0.0
            targets.append(
                TargetPosition(
                    timestamp=signal.timestamp,
                    symbol=signal.symbol,
                    target_fraction=float(max(min(target, 1.0), -1.0)),
                    metadata={
                        "signal": signal,
                        "signal_snapshot": signal.to_dict(),
                        "signal_provenance": signal.provenance.to_dict() if signal.provenance else None,
                    },
                )
            )
        return targets


def create_strategy_from_config(config: StrategyConfig) -> SignalDrivenStrategy:
    params = dict(config.parameters)
    if config.name == "moving_average_crossover":
        return SignalDrivenStrategy(config.name, MovingAverageCrossoverSignal(**params))
    if config.name == "rsi_mean_reversion":
        return SignalDrivenStrategy(config.name, RsiMeanReversionSignal(**params))
    if config.name == "breakout":
        return SignalDrivenStrategy(config.name, BreakoutSignal(**params))
    if config.name == "baseline_ml":
        model_path = params.pop("model_path", None)
        if not model_path:
            raise ValueError("baseline_ml strategy requires parameters.model_path.")
        model = BaselineModel.load(model_path)
        return SignalDrivenStrategy(config.name, MLSignalProvider(model, **params))
    raise ValueError(f"Unknown strategy: {config.name}")
