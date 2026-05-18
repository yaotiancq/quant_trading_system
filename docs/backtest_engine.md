# Backtest Engine

The backtest engine is bar-by-bar and event-driven enough for lightweight research. It supports minute bars, second bars, and any other normalized timestamped OHLCV bars.

## Behavior

- Iterates through timestamps in order.
- Updates latest prices from current bars.
- Submits generated `OrderRequest` objects to a simulated broker.
- The simulated broker owns order IDs, status transitions, latency, expiry, cancellation, open-order exposure, and partial-fill state.
- The execution simulator evaluates each eligible open order against the current OHLCV bar.
- The portfolio module applies fill events and owns cash, position, average price, and realized PnL accounting.
- Supports Alpaca-style `market`, `limit`, `stop`, `stop_limit`, and `trailing_stop` order simulation.
- Supports `day`, `gtc`, `opg`, `cls`, `ioc`, and `fok` time-in-force assumptions.
- Applies configurable market fill assumptions such as next bar open, close, HLC3, OHLC4, or VWAP.
- Applies slippage in basis points after the raw simulated fill price is chosen.
- Applies per-share commissions.
- Supports simple partial fills through `max_fill_volume_pct`.
- Tracks cash, positions, market value, and equity.
- Generates `OrderRequest` objects from strategy logic using only current and past data plus broker/account state.
- Converts signal targets into orders through the shared execution order planner inside the strategy.
- Applies order risk constraints before submitting simulated orders.
- Accounts for pending delayed orders when planning new target deltas.
- Halts new entries and targets open positions flat when `max_daily_loss` is breached for the current session.
- Produces trade logs, equity curves, and metrics.
- Produces diagnostic charts when charting is enabled in the CLI.

Trade logs preserve signal attribution fields from the originating `TradingSignal`, including signal source name, source type, model version, feature set, confidence, confidence metadata, and a serialized signal snapshot. They also include execution fields such as `order_id`, `order_type`, `time_in_force`, `raw_fill_price`, `fill_price`, `fill_reason`, `remaining_quantity`, and the OHLCV bar used for fill simulation.

## Order Lifecycle

The backtest is order-driven:

1. Strategy output is converted into broker-neutral `OrderRequest` objects.
2. Risk checks validate order type, time in force, session, notional, and quantity.
3. The simulated broker accepts orders and assigns backtest order IDs.
4. Orders become eligible after `latency_bars` and, when configured, `latency_seconds`.
5. The execution simulator returns zero, partial, or full fill events.
6. The portfolio applies `FillEvent` objects and updates accounting.
7. The broker updates order status to `accepted`, `partially_filled`, `filled`, `canceled`, or `expired`.

Report artifacts include `orders.csv` for final order state and `order_events.csv` for status transition history.

## Diagnostic Charts

When chart generation is enabled, reports include:

- `equity_curve.png`
- `<SYMBOL>_diagnostics.png`

The symbol diagnostics chart includes candlestick-style OHLC price action, order-submission markers, buy/sell/short/cover fill markers, raw-vs-slipped fill hints, moving averages, VWAP, Bollinger Bands, RSI, MACD, and volume. The charting module also exposes `plot_trade_window` for inspecting a single fill with surrounding bars.

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

By default, strategy signals are generated after bar N is available, then market orders are eligible on bar N+1 and fill at the N+1 open adjusted for slippage. This default is controlled by `market_order_fill: next_open`, which maps to `market_fill_price: open` for the simulator.

OHLCV bars cannot reveal the actual sequence of trades inside a bar, queue priority, spread, or displayed depth. Limit, stop, stop-limit, and trailing-stop orders therefore use explicit bar-level assumptions:

- A buy limit can fill when the bar low touches the limit; a sell limit can fill when the bar high touches the limit.
- Stops trigger when the bar trades through the stop, with gap handling at the open.
- Stop-limit orders must both trigger and be executable at the limit.
- Trailing stops track a high-water mark for sell orders and a low-water mark for buy orders.
- `intrabar_price_path` controls whether ambiguous bars are interpreted as `open_high_low_close` or `open_low_high_close`.
- `max_fill_volume_pct` caps simulated fills as a fraction of the bar volume.

`latency_bars` must be at least `1`, because strategy signals are generated after the current bar is available. `latency_seconds` can add an additional clock-time delay for intraday or second-level bars. Queue position, spread dynamics, borrow availability, margin calls, corporate actions, and exchange-specific microstructure are still not modeled.

The engine supports minute and second bars when normalized data is available. This is intraday research infrastructure, not high-frequency trading infrastructure.
