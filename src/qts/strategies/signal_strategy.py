from __future__ import annotations

import pandas as pd

from qts.config.models import StrategyConfig
from qts.ml.model import BaselineModel
from qts.ml.signal_provider import MLSignalProvider
from qts.execution.order_planner import broker_position_quantities, plan_orders_from_targets
from qts.signals.base import SignalDirection, SignalProvider
from qts.signals.rule_based import BreakoutSignal, MovingAverageCrossoverSignal, RsiMeanReversionSignal
from qts.strategies.base import OrderRequest, TargetPosition


class SignalDrivenStrategy:
    def __init__(self, name: str, signal_provider: SignalProvider, order_defaults: dict[str, object] | None = None) -> None:
        self.name = name
        self.signal_provider = signal_provider
        self.order_defaults = order_defaults or {}

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
                        **self.order_defaults,
                        "signal": signal,
                        "signal_snapshot": signal.to_dict(),
                        "signal_provenance": signal.provenance.to_dict() if signal.provenance else None,
                    },
                )
            )
        return targets

    def generate_orders(self, history: pd.DataFrame, timestamp: pd.Timestamp, broker: object) -> list[OrderRequest]:
        targets = self.generate_targets(history, timestamp)
        account = broker.get_account()
        current_quantities = broker_position_quantities(broker.get_positions())
        pending_quantities = broker.open_order_quantities() if hasattr(broker, "open_order_quantities") else {}
        for symbol, quantity in pending_quantities.items():
            current_quantities[symbol] = current_quantities.get(symbol, 0.0) + quantity
        latest_prices = getattr(broker, "latest_prices", {})
        max_position_notional = float(getattr(broker, "max_position_notional", float("inf")))
        orders = plan_orders_from_targets(
            targets=targets,
            equity=float(getattr(account, "equity")),
            current_quantities=current_quantities,
            latest_prices=latest_prices,
            timestamp=timestamp,
            max_position_notional=max_position_notional,
            strategy_id=self.name,
        )
        return orders


def create_strategy_from_config(config: StrategyConfig) -> SignalDrivenStrategy:
    params = dict(config.parameters)
    order_defaults = _extract_order_defaults(params)
    if config.name == "moving_average_crossover":
        return SignalDrivenStrategy(config.name, MovingAverageCrossoverSignal(**params), order_defaults=order_defaults)
    if config.name == "rsi_mean_reversion":
        return SignalDrivenStrategy(config.name, RsiMeanReversionSignal(**params), order_defaults=order_defaults)
    if config.name == "breakout":
        return SignalDrivenStrategy(config.name, BreakoutSignal(**params), order_defaults=order_defaults)
    if config.name == "baseline_ml":
        model_path = params.pop("model_path", None)
        if not model_path:
            raise ValueError("baseline_ml strategy requires parameters.model_path.")
        model = BaselineModel.load(model_path)
        return SignalDrivenStrategy(config.name, MLSignalProvider(model, **params), order_defaults=order_defaults)
    raise ValueError(f"Unknown strategy: {config.name}")


def _extract_order_defaults(params: dict[str, object]) -> dict[str, object]:
    order_keys = {
        "order_type",
        "time_in_force",
        "limit_price",
        "limit_price_offset_bps",
        "stop_price",
        "stop_price_offset_bps",
        "trail_price",
        "trail_percent",
        "extended_hours",
        "order_class",
    }
    return {key: params.pop(key) for key in list(params) if key in order_keys}
