from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from qts.execution.order_planner import broker_position_quantities, plan_orders_from_targets
from qts.signals.base import SignalDirection, SignalProvenance, SignalType, TradingSignal
from qts.strategies.base import TargetPosition


def test_plan_orders_from_targets_buys_delta_to_target_fraction() -> None:
    timestamp = pd.Timestamp("2024-01-02T14:30:00Z")
    targets = [TargetPosition(timestamp=timestamp.to_pydatetime(), symbol="spy", target_fraction=0.5)]

    orders = plan_orders_from_targets(
        targets=targets,
        equity=10_000,
        current_quantities={"SPY": 5},
        latest_prices={"SPY": 100},
        timestamp=timestamp,
        max_position_notional=10_000,
    )

    assert len(orders) == 1
    assert orders[0].symbol == "SPY"
    assert orders[0].side == "buy"
    assert orders[0].quantity == 45
    assert orders[0].metadata["desired_quantity"] == 50


def test_plan_orders_from_targets_sells_to_flat() -> None:
    timestamp = pd.Timestamp("2024-01-02T14:30:00Z")
    targets = [TargetPosition(timestamp=timestamp.to_pydatetime(), symbol="SPY", target_fraction=0.0)]

    orders = plan_orders_from_targets(
        targets=targets,
        equity=10_000,
        current_quantities={"SPY": 12},
        latest_prices={"SPY": 100},
        timestamp=timestamp,
        max_position_notional=10_000,
    )

    assert len(orders) == 1
    assert orders[0].side == "sell"
    assert orders[0].quantity == 12


def test_plan_orders_skips_missing_prices() -> None:
    timestamp = pd.Timestamp("2024-01-02T14:30:00Z")
    targets = [TargetPosition(timestamp=timestamp.to_pydatetime(), symbol="SPY", target_fraction=1.0)]

    orders = plan_orders_from_targets(
        targets=targets,
        equity=10_000,
        current_quantities={},
        latest_prices={},
        timestamp=timestamp,
        max_position_notional=10_000,
    )

    assert orders == []


def test_plan_orders_caps_position_notional() -> None:
    timestamp = pd.Timestamp("2024-01-02T14:30:00Z")
    targets = [TargetPosition(timestamp=timestamp.to_pydatetime(), symbol="SPY", target_fraction=1.0)]

    orders = plan_orders_from_targets(
        targets=targets,
        equity=100_000,
        current_quantities={},
        latest_prices={"SPY": 100},
        timestamp=timestamp,
        max_position_notional=25_000,
    )

    assert orders[0].quantity == 250
    assert orders[0].metadata["target_notional"] == 25_000


def test_broker_position_quantities_normalizes_alpaca_like_positions() -> None:
    @dataclass(frozen=True)
    class Position:
        symbol: str
        qty: str

    positions = [Position(symbol="spy", qty="3.5"), Position(symbol="AAPL", qty="-2")]

    assert broker_position_quantities(positions) == {"SPY": 3.5, "AAPL": -2.0}


def test_plan_orders_preserves_signal_provenance_metadata() -> None:
    timestamp = pd.Timestamp("2024-01-02T14:30:00Z")
    signal = TradingSignal(
        timestamp=timestamp.to_pydatetime(),
        symbol="SPY",
        signal_type=SignalType.ML,
        direction=SignalDirection.LONG,
        strength=0.8,
        confidence=0.9,
        target_position=0.5,
        provenance=SignalProvenance(
            source_name="baseline_ml",
            source_type=SignalType.ML,
            model_version="baseline_logistic_v1",
            feature_set=("return_1", "ma_ratio_5_20"),
        ),
        confidence_metadata={"method": "model_probability", "probability_up": 0.9},
    )
    target = TargetPosition(
        timestamp=timestamp.to_pydatetime(),
        symbol="SPY",
        target_fraction=0.5,
        metadata={"signal": signal, "signal_snapshot": signal.to_dict(), "signal_provenance": signal.provenance.to_dict()},
    )

    orders = plan_orders_from_targets(
        targets=[target],
        equity=10_000,
        current_quantities={},
        latest_prices={"SPY": 100},
        timestamp=timestamp,
        max_position_notional=10_000,
    )

    assert orders[0].metadata["signal_source_name"] == "baseline_ml"
    assert orders[0].metadata["signal_source_type"] == "ML"
    assert orders[0].metadata["signal_model_version"] == "baseline_logistic_v1"
    assert orders[0].metadata["signal_feature_set"] == ["return_1", "ma_ratio_5_20"]
    assert orders[0].metadata["signal_confidence"] == 0.9
    assert orders[0].metadata["signal_confidence_metadata"]["probability_up"] == 0.9


def test_plan_orders_supports_limit_order_offsets() -> None:
    timestamp = pd.Timestamp("2024-01-02T14:30:00Z")
    target = TargetPosition(
        timestamp=timestamp.to_pydatetime(),
        symbol="SPY",
        target_fraction=0.5,
        metadata={"order_type": "limit", "time_in_force": "gtc", "limit_price_offset_bps": 10},
    )

    orders = plan_orders_from_targets(
        targets=[target],
        equity=10_000,
        current_quantities={},
        latest_prices={"SPY": 100},
        timestamp=timestamp,
        max_position_notional=10_000,
    )

    assert orders[0].order_type == "limit"
    assert orders[0].time_in_force == "gtc"
    assert orders[0].limit_price == 99.9
