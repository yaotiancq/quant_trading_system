# Backtest Engine

The backtest engine is bar-by-bar and event-driven enough for lightweight research. It supports minute bars, second bars, and any other normalized timestamped OHLCV bars.

## Behavior

- Iterates through timestamps in order.
- Updates latest prices from current bars.
- Fills pending market orders after configurable `latency_bars`.
- Applies slippage in basis points.
- Applies per-share commissions.
- Tracks cash, positions, market value, and equity.
- Generates target positions from strategy logic using only current and past data.
- Converts targets into orders through the shared execution order planner.
- Applies risk constraints before creating orders.
- Halts new entries and targets open positions flat when `max_daily_loss` is breached for the current session.
- Produces trade logs, equity curves, and metrics.
- Produces diagnostic charts when charting is enabled in the CLI.

Trade logs preserve signal attribution fields from the originating `TradingSignal`, including signal source name, source type, model version, feature set, confidence, confidence metadata, and a serialized signal snapshot.

## Diagnostic Charts

When chart generation is enabled, reports include:

- `equity_curve.png`
- `<SYMBOL>_diagnostics.png`

The symbol diagnostics chart includes candlestick-style OHLC price action, buy/sell markers, moving averages, VWAP, Bollinger Bands, RSI, MACD, and volume. The charting module also exposes `plot_trade_window` for inspecting a single fill with surrounding bars.

## Metrics

- total return
- annualized return
- max drawdown
- Sharpe ratio
- win rate
- profit factor
- average trade return
- number of trades
- exposure time
- average holding period

## Assumptions

Market orders fill at the next eligible bar close adjusted for slippage. `latency_bars` must be at least `1`, because strategy signals are generated after the current bar is available. Partial fills, queue position, borrow availability, corporate actions, and exchange-specific microstructure are not modeled in the initial version.
