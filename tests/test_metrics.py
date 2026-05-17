from __future__ import annotations

import pandas as pd

from qts.backtest.metrics import calculate_performance_metrics


def test_metrics_include_required_fields() -> None:
    equity_curve = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02", periods=4, freq="D"),
            "equity": [100_000, 101_000, 99_000, 103_000],
            "gross_exposure": [0.0, 0.5, 0.5, 0.0],
        }
    )
    trades = pd.DataFrame(
        {
            "realized_pnl": [500.0, -200.0],
            "trade_return": [0.05, -0.02],
            "holding_period_bars": [2, 3],
        }
    )

    metrics = calculate_performance_metrics(equity_curve, trades)

    expected = {
        "total_return",
        "annualized_return",
        "max_drawdown",
        "sharpe_ratio",
        "win_rate",
        "profit_factor",
        "average_trade_return",
        "number_of_trades",
        "exposure_time",
        "average_holding_period",
    }
    assert expected.issubset(metrics)
    assert metrics["number_of_trades"] == 2.0
    assert metrics["win_rate"] == 0.5
