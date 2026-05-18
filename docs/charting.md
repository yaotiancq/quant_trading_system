# Charting And Visualization

The charting module is part of the research and backtesting workflow. It is designed for quick visual validation of strategy logic before deeper quantitative analysis.

## Built-In Outputs

Backtest reports can generate:

```text
equity_curve.png
<SYMBOL>_diagnostics.png
```

The diagnostics chart includes:

- candlestick-style OHLC price action
- buy, sell, short, and cover fill markers
- raw fill price markers and slippage lines when simulated fill price differs from raw bar price
- optional order-submission markers from `orders.csv`
- moving averages
- VWAP
- Bollinger Bands
- RSI
- MACD
- volume

## Programmatic Use

```python
from qts.reporting import plot_strategy_diagnostics, plot_trade_window

plot_strategy_diagnostics(
    bars=data,
    trades=result.trades,
    output_path="reports/backtests/SPY_diagnostics.png",
    symbol="SPY",
    orders=result.orders,
)

plot_trade_window(
    bars=data,
    trades=result.trades,
    trade_index=0,
    output_path="reports/backtests/SPY_trade_0.png",
    orders=result.orders,
)
```

## Extending

Custom indicators, model outputs, or diagnostic columns can be plotted by adding them to the bars DataFrame and passing their column names as custom panels:

```python
plot_strategy_diagnostics(
    bars=data_with_model_score,
    trades=result.trades,
    output_path="reports/backtests/SPY_model_diagnostics.png",
    symbol="SPY",
    oscillator_panels=["rsi", "macd", "model_score"],
)
```

Keep diagnostics lightweight. The goal is fast inspection of whether entries, exits, and signal timing look reasonable, not a full dashboard.
