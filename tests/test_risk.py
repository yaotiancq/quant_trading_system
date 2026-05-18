from __future__ import annotations

import pandas as pd

from qts.config.models import RiskConfig
from qts.risk.manager import RiskManager
from qts.strategies.base import OrderRequest, TargetPosition


def test_risk_manager_scales_gross_exposure() -> None:
    timestamp = pd.Timestamp("2024-01-02T14:30:00Z").to_pydatetime()
    manager = RiskManager(RiskConfig(max_gross_exposure=0.5, max_symbol_exposure=1.0))
    targets = [
        TargetPosition(timestamp, "SPY", 0.5),
        TargetPosition(timestamp, "AAPL", -0.5),
    ]

    approved = manager.validate_targets(targets)

    assert sum(abs(target.target_fraction) for target in approved) == 0.5


def test_risk_manager_blocks_shorts_when_disabled() -> None:
    timestamp = pd.Timestamp("2024-01-02T14:30:00Z").to_pydatetime()
    manager = RiskManager(RiskConfig(allow_short=False))

    approved = manager.validate_targets([TargetPosition(timestamp, "SPY", -0.25)])

    assert approved[0].target_fraction == 0.0


def test_risk_manager_clips_order_notional_and_quantity() -> None:
    timestamp = pd.Timestamp("2024-01-02T14:30:00Z")
    manager = RiskManager(RiskConfig(max_order_notional=1_000, max_position_quantity=8))
    order = OrderRequest(timestamp.to_pydatetime(), "SPY", "buy", 100)

    approved = manager.validate_orders([order], {"SPY": 100.0}, timestamp)

    assert len(approved) == 1
    assert approved[0].quantity == 8
    assert approved[0].metadata["risk_max_order_notional"] == 1_000


def test_risk_manager_respects_session_filter() -> None:
    manager = RiskManager(RiskConfig(trading_session_start="06:30", trading_session_end="13:00"))

    assert manager.is_trading_session_open(pd.Timestamp("2024-01-02T06:30:00"))
    assert not manager.is_trading_session_open(pd.Timestamp("2024-01-02T15:00:00"))


def test_risk_manager_rejects_unsupported_order_type_tif_combo() -> None:
    timestamp = pd.Timestamp("2024-01-02T14:30:00Z")
    manager = RiskManager(RiskConfig())
    order = OrderRequest(
        timestamp.to_pydatetime(),
        "SPY",
        "buy",
        10,
        order_type="stop",
        time_in_force="ioc",
        stop_price=101,
    )

    assert manager.validate_orders([order], {"SPY": 100.0}, timestamp) == []
