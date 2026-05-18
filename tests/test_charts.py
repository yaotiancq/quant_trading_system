from __future__ import annotations

from pathlib import Path

from qts.backtest.engine import BacktestEngine
from qts.config.loader import load_app_config
from qts.data.loader import load_market_data
from qts.reporting.charts import plot_strategy_diagnostics, plot_trade_window
from qts.reporting.reports import write_backtest_report
from qts.risk.manager import RiskManager
from qts.strategies.signal_strategy import create_strategy_from_config


def _sample_result():
    config = load_app_config("configs/backtest.yaml")
    data = load_market_data(config.data)
    strategy = create_strategy_from_config(config.strategy)
    result = BacktestEngine(config.backtest, strategy, RiskManager(config.risk)).run(data)
    return data, result


def test_plot_strategy_diagnostics_creates_file(tmp_path: Path) -> None:
    data, result = _sample_result()
    output = tmp_path / "spy_diagnostics.png"

    plot_strategy_diagnostics(data, result.trades, output, symbol="SPY")

    assert output.exists()
    assert output.stat().st_size > 0


def test_write_backtest_report_creates_diagnostic_chart(tmp_path: Path) -> None:
    data, result = _sample_result()

    write_backtest_report(result, tmp_path, make_chart=True, market_data=data)

    assert (tmp_path / "equity_curve.png").exists()
    assert (tmp_path / "SPY_diagnostics.png").exists()


def test_plot_trade_window_creates_file(tmp_path: Path) -> None:
    data, result = _sample_result()
    output = tmp_path / "trade_window.png"

    plot_trade_window(data, result.trades, trade_index=0, output_path=output, orders=result.orders)

    assert output.exists()
    assert output.stat().st_size > 0


def test_plot_strategy_diagnostics_supports_order_driven_sides(tmp_path: Path) -> None:
    data, result = _sample_result()
    timestamp = data["timestamp"].iloc[30]
    trades = result.trades.head(0).copy()
    orders = result.orders.head(0).copy()

    for index, side in enumerate(["buy", "sell", "sell_short", "buy_to_cover"]):
        trades.loc[index, "timestamp"] = timestamp
        trades.loc[index, "symbol"] = "SPY"
        trades.loc[index, "side"] = side
        trades.loc[index, "fill_price"] = float(data["close"].iloc[30]) + index
        trades.loc[index, "raw_fill_price"] = float(data["close"].iloc[30]) + index - 0.1
        trades.loc[index, "fill_status"] = "partially_filled" if index == 0 else "filled"
        trades.loc[index, "order_id"] = f"ORD-{index}"

        orders.loc[index, "submitted_at"] = timestamp
        orders.loc[index, "ready_at"] = timestamp
        orders.loc[index, "symbol"] = "SPY"
        orders.loc[index, "side"] = side
        orders.loc[index, "status"] = "filled"
        orders.loc[index, "order_type"] = "market"

    output = tmp_path / "order_driven_sides.png"

    plot_strategy_diagnostics(
        data.iloc[:80],
        trades,
        output,
        symbol="SPY",
        oscillator_panels=[],
        orders=orders,
    )

    assert output.exists()
    assert output.stat().st_size > 0
