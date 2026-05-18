from __future__ import annotations

import pandas as pd

from qts.backtest.execution import BarExecutionSimulator
from qts.config.models import BacktestConfig
from qts.strategies.base import OrderRequest


def _bar(open_: float = 100, high: float = 105, low: float = 95, close: float = 102) -> pd.Series:
    return pd.Series(
        {
            "timestamp": pd.Timestamp("2024-01-02T14:31:00Z"),
            "symbol": "SPY",
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": 10_000,
            "vwap": (open_ + high + low + close) / 4,
        }
    )


def test_market_order_uses_configured_open_fill_price() -> None:
    simulator = BarExecutionSimulator(BacktestConfig(market_fill_price="open"))
    order = OrderRequest(pd.Timestamp("2024-01-02T14:30:00Z").to_pydatetime(), "SPY", "buy", 10)

    fill = simulator.simulate(order, _bar(open_=101, close=110))

    assert fill.status == "filled"
    assert fill.fill_price == 101
    assert fill.reason == "market_open"


def test_limit_order_fills_when_bar_touches_limit() -> None:
    simulator = BarExecutionSimulator(BacktestConfig())
    order = OrderRequest(
        pd.Timestamp("2024-01-02T14:30:00Z").to_pydatetime(),
        "SPY",
        "buy",
        10,
        order_type="limit",
        limit_price=99,
    )

    fill = simulator.simulate(order, _bar(open_=101, high=102, low=98, close=100))

    assert fill.status == "filled"
    assert fill.fill_price == 99


def test_stop_limit_order_can_trigger_without_fill_on_gap() -> None:
    simulator = BarExecutionSimulator(BacktestConfig())
    order = OrderRequest(
        pd.Timestamp("2024-01-02T14:30:00Z").to_pydatetime(),
        "SPY",
        "buy",
        10,
        order_type="stop_limit",
        stop_price=101,
        limit_price=102,
    )

    fill = simulator.simulate(order, _bar(open_=104, high=106, low=103, close=105))

    assert not fill.has_fill
    assert fill.reason == "stop_limit_not_executable"


def test_trailing_stop_tracks_high_water_mark_and_triggers() -> None:
    simulator = BarExecutionSimulator(BacktestConfig(intrabar_price_path="open_high_low_close"))
    order = OrderRequest(
        pd.Timestamp("2024-01-02T14:30:00Z").to_pydatetime(),
        "SPY",
        "sell",
        10,
        order_type="trailing_stop",
        trail_price=2.0,
    )

    fill = simulator.simulate(order, _bar(open_=100, high=105, low=102, close=103), trail_hwm=101)

    assert fill.has_fill
    assert fill.fill_price == 103
    assert fill.trail_hwm == 105
