from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from qts.backtest.broker import BacktestBroker
from qts.backtest.engine import BacktestEngine
from qts.backtest.fills import FillEvent
from qts.backtest.orders import OrderRequest, OrderSide
from qts.backtest.portfolio import Portfolio
from qts.config.loader import EnvSettings
from qts.config.models import BacktestConfig, RiskConfig
from qts.execution.alpaca_broker import AlpacaLiveBroker, AlpacaPaperBroker
from qts.execution.broker import BrokerAdapter
from qts.signals.base import SignalDirection, SignalType, TradingSignal
from qts.strategies.signal_strategy import SignalDrivenStrategy


class FixedSignalProvider:
    name = "fixed"

    def generate(self, history: pd.DataFrame, timestamp: pd.Timestamp) -> list[TradingSignal]:
        return [
            TradingSignal(
                timestamp=timestamp.to_pydatetime(),
                symbol="SPY",
                signal_type=SignalType.RULE_BASED,
                direction=SignalDirection.LONG,
                target_position=0.5,
            )
        ]


def test_backtest_and_alpaca_paper_brokers_share_adapter_contract() -> None:
    backtest_broker = BacktestBroker(BacktestConfig())
    paper_broker = AlpacaPaperBroker.__new__(AlpacaPaperBroker)

    assert isinstance(backtest_broker, BrokerAdapter)
    assert isinstance(paper_broker, BrokerAdapter)


def test_strategy_produces_order_requests_against_broker_interface() -> None:
    strategy = SignalDrivenStrategy("fixed_strategy", FixedSignalProvider())
    broker = BacktestBroker(BacktestConfig(initial_cash=100_000))
    broker.latest_prices["SPY"] = 100.0

    orders = strategy.generate_orders(
        history=_bars(),
        timestamp=pd.Timestamp("2024-01-02T14:30:00Z"),
        broker=broker,
    )

    assert len(orders) == 1
    assert isinstance(orders[0], OrderRequest)
    assert orders[0].side == OrderSide.BUY
    assert orders[0].strategy_id == "fixed_strategy"


def test_same_strategy_works_with_alpaca_paper_broker_interface_mock() -> None:
    strategy = SignalDrivenStrategy("fixed_strategy", FixedSignalProvider())
    paper_broker = Mock(spec=AlpacaPaperBroker)
    paper_broker.get_account.return_value = SimpleNamespace(equity=100_000.0)
    paper_broker.get_positions.return_value = []
    paper_broker.latest_prices = {"SPY": 100.0}

    orders = strategy.generate_orders(
        history=_bars(),
        timestamp=pd.Timestamp("2024-01-02T14:30:00Z"),
        broker=paper_broker,
    )

    assert len(orders) == 1
    assert isinstance(orders[0], OrderRequest)


def test_portfolio_public_accounting_mutation_uses_fill_events() -> None:
    portfolio = Portfolio(initial_cash=10_000)

    fill = FillEvent(
        fill_id="FILL-1",
        order_id="ORD-1",
        timestamp=pd.Timestamp("2024-01-02T14:31:00Z").to_pydatetime(),
        symbol="SPY",
        side="buy",
        quantity=10,
        fill_price=100,
    )
    portfolio.apply_fill_event(fill)

    assert not hasattr(portfolio, "apply_fill")
    assert portfolio.positions["SPY"].quantity == 10
    assert portfolio.fill_history == [fill]


def test_backtest_engine_submits_only_risk_checked_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    sequence: list[str] = []

    class OneOrderStrategy:
        name = "one_order"

        def generate_orders(self, history: pd.DataFrame, timestamp: pd.Timestamp, broker: object) -> list[OrderRequest]:
            if broker.get_open_orders() or broker.get_positions():
                return []
            return [OrderRequest(timestamp.to_pydatetime(), "SPY", "buy", 1)]

    class RecordingRiskManager:
        config = RiskConfig(max_daily_loss=5_000)

        def validate_orders(
            self,
            orders: list[OrderRequest],
            latest_prices: dict[str, float],
            timestamp: pd.Timestamp,
        ) -> list[OrderRequest]:
            sequence.append("risk")
            return [
                OrderRequest(
                    timestamp=order.timestamp,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.quantity,
                    notional=order.notional,
                    order_type=order.order_type,
                    limit_price=order.limit_price,
                    stop_price=order.stop_price,
                    time_in_force=order.time_in_force,
                    strategy_id=order.strategy_id,
                    metadata={**order.metadata, "risk_checked": True},
                )
                for order in orders
            ]

    original_submit = BacktestBroker.submit_order

    def checked_submit(self: BacktestBroker, order: OrderRequest) -> object:
        sequence.append("submit")
        assert order.metadata["risk_checked"] is True
        return original_submit(self, order)

    monkeypatch.setattr(BacktestBroker, "submit_order", checked_submit)

    BacktestEngine(
        BacktestConfig(initial_cash=100_000, latency_bars=1),
        OneOrderStrategy(),
        RecordingRiskManager(),
    ).run(_bars())

    assert sequence[:2] == ["risk", "submit"]


def test_backtest_engine_does_not_mutate_portfolio_directly() -> None:
    source = inspect.getsource(BacktestEngine.run)

    assert "Portfolio(" not in source
    assert "apply_fill" not in source
    assert ".positions" not in source


def test_live_broker_is_disabled_unless_explicitly_enabled() -> None:
    with pytest.raises(ValueError, match="disabled by default"):
        AlpacaLiveBroker(EnvSettings(), live_trading_enabled=False)


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2024-01-02T14:30:00Z"),
                "symbol": "SPY",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 10_000,
                "vwap": 100.0,
            }
        ]
    )
