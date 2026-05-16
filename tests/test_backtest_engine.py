import pandas as pd

from qts.backtest.engine import BacktestEngine
from qts.backtest.portfolio import Portfolio
from qts.config.models import BacktestConfig, DataConfig, RiskConfig
from qts.config.loader import load_app_config
from qts.data.validation import normalize_market_data
from qts.data.loader import load_market_data
from qts.risk.manager import RiskManager
from qts.strategies.base import TargetPosition
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
    portfolio.apply_fill("SPY", signed_quantity=10, fill_price=100, commission=0)
    fill = portfolio.apply_fill("SPY", signed_quantity=-4, fill_price=110, commission=1)

    assert fill.closed_quantity == 4
    assert fill.realized_pnl == 39
    assert portfolio.positions["SPY"].quantity == 6
    assert portfolio.positions["SPY"].average_price == 100


def test_portfolio_reversal_resets_average_price_to_reversal_fill() -> None:
    portfolio = Portfolio(initial_cash=10_000)
    portfolio.apply_fill("SPY", signed_quantity=10, fill_price=100, commission=0)
    fill = portfolio.apply_fill("SPY", signed_quantity=-15, fill_price=110, commission=0)

    assert fill.closed_quantity == 10
    assert fill.realized_pnl == 100
    assert portfolio.positions["SPY"].quantity == -5
    assert portfolio.positions["SPY"].average_price == 110


def test_backtest_daily_loss_guard_flattens_positions() -> None:
    class AlwaysLongStrategy:
        name = "always_long"

        def generate_targets(self, history: pd.DataFrame, timestamp: pd.Timestamp) -> list[TargetPosition]:
            return [TargetPosition(timestamp=timestamp.to_pydatetime(), symbol="SPY", target_fraction=1.0)]

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
