import pandas as pd

from qts.backtest.engine import BacktestEngine
from qts.backtest.fills import FillEvent
from qts.backtest.portfolio import Portfolio
from qts.config.models import BacktestConfig, DataConfig, RiskConfig
from qts.config.loader import load_app_config
from qts.data.validation import normalize_market_data
from qts.data.loader import load_market_data
from qts.risk.manager import RiskManager
from qts.backtest.orders import OrderRequest, OrderSide
from qts.strategies.signal_strategy import create_strategy_from_config


def test_backtest_engine_runs_on_sample_data() -> None:
    config = load_app_config("configs/backtest.yaml")
    data = load_market_data(DataConfig(data_file="data/raw/sample_bars.csv", source="local", symbols=["SPY"]))
    strategy = create_strategy_from_config(config.strategy)
    engine = BacktestEngine(config.backtest, strategy, RiskManager(config.risk))
    result = engine.run(data)
    assert not result.equity_curve.empty
    assert "total_return" in result.metrics
    assert "max_drawdown" in result.metrics


def test_portfolio_partial_close_preserves_average_price() -> None:
    portfolio = Portfolio(initial_cash=10_000)
    portfolio.apply_fill_event(_fill("FILL-1", "ORD-1", "SPY", "buy", 10, 100, 0))
    fill = portfolio.apply_fill_event(_fill("FILL-2", "ORD-2", "SPY", "sell", 4, 110, 1))

    assert fill.closed_quantity == 4
    assert fill.realized_pnl == 39
    assert portfolio.positions["SPY"].quantity == 6
    assert portfolio.positions["SPY"].average_price == 100


def test_portfolio_reversal_resets_average_price_to_reversal_fill() -> None:
    portfolio = Portfolio(initial_cash=10_000)
    portfolio.apply_fill_event(_fill("FILL-1", "ORD-1", "SPY", "buy", 10, 100, 0))
    fill = portfolio.apply_fill_event(_fill("FILL-2", "ORD-2", "SPY", "sell", 15, 110, 0))

    assert fill.closed_quantity == 10
    assert fill.realized_pnl == 100
    assert portfolio.positions["SPY"].quantity == -5
    assert portfolio.positions["SPY"].average_price == 110


def test_backtest_daily_loss_guard_flattens_positions() -> None:
    class AlwaysLongStrategy:
        name = "always_long"

        def generate_orders(self, history: pd.DataFrame, timestamp: pd.Timestamp, broker: object) -> list[OrderRequest]:
            if broker.get_positions() or broker.get_open_orders():
                return []
            return [OrderRequest(timestamp=timestamp.to_pydatetime(), symbol="SPY", side=OrderSide.BUY, quantity=100)]

    rows = []
    for index, close in enumerate([100.0, 80.0, 70.0, 70.0]):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-02T14:30:00Z") + pd.Timedelta(minutes=index),
                "symbol": "SPY",
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": 1_000,
            }
        )
    data = normalize_market_data(pd.DataFrame(rows))
    engine = BacktestEngine(
        BacktestConfig(initial_cash=10_000, latency_bars=1),
        AlwaysLongStrategy(),
        RiskManager(RiskConfig(max_daily_loss=500, max_position_notional=10_000)),
    )

    result = engine.run(data)

    assert result.equity_curve["risk_halted"].any()
    assert result.trades.iloc[-1]["position_after"] == 0.0


def test_backtest_market_order_fills_on_next_bar_open() -> None:
    class AlwaysLongStrategy:
        name = "always_long"

        def generate_orders(self, history: pd.DataFrame, timestamp: pd.Timestamp, broker: object) -> list[OrderRequest]:
            if broker.get_positions() or broker.get_open_orders():
                return []
            return [OrderRequest(timestamp=timestamp.to_pydatetime(), symbol="SPY", side=OrderSide.BUY, quantity=50)]

    rows = [
        {
            "timestamp": pd.Timestamp("2024-01-02T14:30:00Z"),
            "symbol": "SPY",
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 10_000,
        },
        {
            "timestamp": pd.Timestamp("2024-01-02T14:31:00Z"),
            "symbol": "SPY",
            "open": 105.0,
            "high": 121.0,
            "low": 104.0,
            "close": 120.0,
            "volume": 10_000,
        },
    ]
    data = normalize_market_data(pd.DataFrame(rows))
    engine = BacktestEngine(
        BacktestConfig(initial_cash=10_000, latency_bars=1, market_fill_price="open"),
        AlwaysLongStrategy(),
        RiskManager(RiskConfig(max_position_notional=10_000)),
    )

    result = engine.run(data)

    assert result.trades.iloc[0]["raw_fill_price"] == 105.0
    assert result.trades.iloc[0]["fill_bar_open"] == 105.0
    assert result.trades.iloc[0]["fill_bar_close"] == 120.0
    assert result.trades.iloc[0]["order_id"] == result.orders.iloc[0]["order_id"]
    assert result.orders.iloc[0]["status"] == "filled"
    assert "accepted" in set(result.order_events["status"])


def test_backtest_engine_expires_open_orders_at_end() -> None:
    class FarLimitStrategy:
        name = "far_limit"

        def generate_orders(self, history: pd.DataFrame, timestamp: pd.Timestamp, broker: object) -> list[OrderRequest]:
            if broker.get_open_orders() or not broker.latest_prices:
                return []
            return [
                OrderRequest(
                    timestamp=timestamp.to_pydatetime(),
                    symbol="SPY",
                    side=OrderSide.BUY,
                    quantity=10,
                    order_type="limit",
                    limit_price=50,
                    time_in_force="gtc",
                )
            ]

    rows = []
    for index in range(2):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-02T14:30:00Z") + pd.Timedelta(minutes=index),
                "symbol": "SPY",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 10_000,
            }
        )
    data = normalize_market_data(pd.DataFrame(rows))

    result = BacktestEngine(
        BacktestConfig(initial_cash=10_000, latency_bars=1),
        FarLimitStrategy(),
        RiskManager(RiskConfig(max_position_notional=10_000)),
    ).run(data)

    assert result.orders.iloc[0]["status"] == "expired"
    assert result.orders.iloc[0]["status_reason"] == "end_of_backtest"


def _fill(
    fill_id: str,
    order_id: str,
    symbol: str,
    side: str,
    quantity: float,
    fill_price: float,
    commission: float,
) -> FillEvent:
    return FillEvent(
        fill_id=fill_id,
        order_id=order_id,
        timestamp=pd.Timestamp("2024-01-02T14:31:00Z").to_pydatetime(),
        symbol=symbol,
        side=side,
        quantity=quantity,
        fill_price=fill_price,
        commission=commission,
    )
