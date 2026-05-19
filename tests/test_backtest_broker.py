from __future__ import annotations

import pandas as pd

from qts.backtest.broker import OrderStatus, SimulatedBroker
from qts.config.models import BacktestConfig
from qts.strategies.base import OrderRequest


def _bars(open_: float = 100, high: float = 101, low: float = 99, close: float = 100, volume: float = 1_000) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2024-01-02T14:31:00Z"),
                "symbol": "SPY",
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "vwap": (open_ + high + low + close) / 4,
            }
        ]
    )


def test_simulated_broker_submits_tracks_and_fills_market_order() -> None:
    broker = SimulatedBroker(BacktestConfig(latency_bars=1, market_fill_price="open"))
    submitted_at = pd.Timestamp("2024-01-02T14:30:00Z")
    order = OrderRequest(submitted_at.to_pydatetime(), "SPY", "buy", 10)

    broker.set_clock(submitted_at, bar_index=0)
    record = broker.submit_order(order)
    early_fills = broker.process_bar(submitted_at, bar_index=0, bars=_bars())
    fills = broker.process_bar(pd.Timestamp("2024-01-02T14:31:00Z"), bar_index=1, bars=_bars(open_=101))

    assert early_fills == []
    assert len(fills) == 1
    assert fills[0].order_id == record.order_id
    assert fills[0].raw_fill_price == 101
    assert broker.get_order_status(record.order_id) == OrderStatus.FILLED
    assert broker.order_log().iloc[0]["status"] == "filled"


def test_simulated_broker_keeps_gtc_limit_order_open_until_touched() -> None:
    broker = SimulatedBroker(BacktestConfig(latency_bars=1))
    submitted_at = pd.Timestamp("2024-01-02T14:30:00Z")
    order = OrderRequest(
        submitted_at.to_pydatetime(),
        "SPY",
        "buy",
        10,
        order_type="limit",
        time_in_force="gtc",
        limit_price=95,
    )

    broker.set_clock(submitted_at, bar_index=0)
    record = broker.submit_order(order)
    no_fill = broker.process_bar(pd.Timestamp("2024-01-02T14:31:00Z"), bar_index=1, bars=_bars(low=96))
    fill = broker.process_bar(pd.Timestamp("2024-01-02T14:32:00Z"), bar_index=2, bars=_bars(low=94))

    assert no_fill == []
    assert broker.order_events().iloc[-1]["reason"] == "limit_touched"
    assert len(fill) == 1
    assert broker.get_order_status(record.order_id) == OrderStatus.FILLED


def test_simulated_broker_records_partial_fill_and_remaining_quantity() -> None:
    broker = SimulatedBroker(BacktestConfig(latency_bars=1, max_fill_volume_pct=0.1, allow_partial_fills=True))
    submitted_at = pd.Timestamp("2024-01-02T14:30:00Z")
    order = OrderRequest(submitted_at.to_pydatetime(), "SPY", "buy", 50)

    broker.set_clock(submitted_at, bar_index=0)
    record = broker.submit_order(order)
    fills = broker.process_bar(pd.Timestamp("2024-01-02T14:31:00Z"), bar_index=1, bars=_bars(volume=100))

    assert len(fills) == 1
    assert fills[0].filled_quantity == 10
    assert fills[0].remaining_quantity == 40
    assert broker.get_order_status(record.order_id) == OrderStatus.PARTIALLY_FILLED
    assert broker.open_order_quantities() == {"SPY": 40}


def test_simulated_broker_respects_latency_seconds() -> None:
    broker = SimulatedBroker(BacktestConfig(latency_bars=1, latency_seconds=60, market_fill_price="open"))
    submitted_at = pd.Timestamp("2024-01-02T14:30:00Z")
    order = OrderRequest(submitted_at.to_pydatetime(), "SPY", "buy", 10)

    broker.set_clock(submitted_at, bar_index=0)
    record = broker.submit_order(order)
    early = broker.process_bar(pd.Timestamp("2024-01-02T14:30:30Z"), bar_index=1, bars=_bars(open_=101))
    filled = broker.process_bar(pd.Timestamp("2024-01-02T14:31:00Z"), bar_index=2, bars=_bars(open_=102))

    assert early == []
    assert len(filled) == 1
    assert filled[0].raw_fill_price == 102
    assert broker.get_order_status(record.order_id) == OrderStatus.FILLED


def test_simulated_broker_rejects_buy_without_cash() -> None:
    broker = SimulatedBroker(BacktestConfig(initial_cash=1_000, latency_bars=1, enforce_buying_power=True))
    submitted_at = pd.Timestamp("2024-01-02T14:30:00Z")
    broker.latest_prices["SPY"] = 100.0
    broker.set_clock(submitted_at, bar_index=0)

    record = broker.submit_order(OrderRequest(submitted_at.to_pydatetime(), "SPY", "buy", 20))

    assert broker.get_order_status(record.order_id) == OrderStatus.REJECTED
    assert broker.order_log().iloc[0]["status_reason"] == "insufficient_cash"


def test_simulated_broker_finalizes_open_orders_at_end_of_backtest() -> None:
    broker = SimulatedBroker(BacktestConfig(latency_bars=1))
    submitted_at = pd.Timestamp("2024-01-02T14:30:00Z")
    order = OrderRequest(
        submitted_at.to_pydatetime(),
        "SPY",
        "buy",
        10,
        order_type="limit",
        time_in_force="gtc",
        limit_price=50,
    )

    broker.set_clock(submitted_at, bar_index=0)
    record = broker.submit_order(order)
    broker.process_bar(pd.Timestamp("2024-01-02T14:31:00Z"), bar_index=1, bars=_bars(low=90))
    broker.finalize(pd.Timestamp("2024-01-02T14:31:00Z"))

    assert broker.get_order_status(record.order_id) == OrderStatus.EXPIRED
    assert broker.order_log().iloc[0]["status_reason"] == "end_of_backtest"
