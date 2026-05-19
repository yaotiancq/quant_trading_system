# Changelog

## 2026-05-18 BrokerAdapter Architecture Refactor

- Added canonical backtest order models in `qts.backtest.orders` and fill models in `qts.backtest.fills`.
- Added `BacktestBroker` as the backtest implementation of the shared `BrokerAdapter` interface.
- Added `AlpacaPaperBroker` and disabled-by-default `AlpacaLiveBroker` behavior.
- Refactored strategies to produce standardized `OrderRequest` objects through `generate_orders(...)`.
- Refactored `BacktestEngine` so it orchestrates time, risk validation, and broker submission without directly changing cash or positions.
- Restricted portfolio public accounting mutation to `FillEvent` processing.
- Added `ExecutionSimulator` alias for the OHLCV bar execution simulator.
- Updated configs with explicit `execution`, `broker`, and order-risk fields.
- Added architecture tests for BrokerAdapter conformance, risk-before-submit ordering, fill-event-only portfolio updates, and live broker safety.
- Updated documentation to explain the mode-independent execution flow.
- Updated charting to visualize order submissions, buy/sell/short/cover fills, partial fills, and raw-vs-slipped fill prices.
- Split reversal targets into explicit close/open order legs.
- Added strict order-side validation so `SELL` and `BUY_TO_COVER` cannot accidentally open opposite-side positions.
- Added liquidation-specific risk validation that bypasses normal order-size caps for max-loss and kill-switch flattening.
- Made limit, stop, and stop-limit fills respect the configured intrabar price path.
- Added end-of-backtest expiration for remaining open orders.
- Added simple buying-power and max-leverage checks to the simulated broker.
- Disabled `current_close` market fills by default and added timeframe-aware metric annualization.

## 2026-05-17

- Added deterministic sample data generator and regenerated `data/raw/sample_bars.csv`.
- Updated default configs to support credential-free local backtesting and safe dry-run paper trading.
- Added support for required Alpaca environment variable names.
- Expanded technical features with log returns, RSI, VWAP deviation, volume statistics, and momentum.
- Added breakout signal provider and enhanced signal combiner conflict handling.
- Added order-level risk validation, session filtering, max order notional, max quantity, and kill-switch behavior.
- Improved backtest order planning with pending-order awareness under latency.
- Added markdown backtest summaries.
- Added dry-run paper loop helper and safer CLI behavior.
- Added compatibility modules matching the documented project structure.
- Added tests for features, metrics, risk, signal combination, and data validation.
- Added risk management and CLI documentation plus continuity files.

## 2026-05-17 Backtest Execution Simulation Update

- Replaced close-price-only fill simulation with an OHLCV bar execution simulator.
- Added support for `market`, `limit`, `stop`, `stop_limit`, and `trailing_stop` order simulation.
- Added support for `day`, `gtc`, `opg`, `cls`, `ioc`, and `fok` time-in-force assumptions.
- Added configurable market fill price models: `open`, `close`, `hlc3`, `ohlc4`, and `vwap`.
- Added configurable limit, stop, intrabar path, partial-fill, and max bar volume assumptions.
- Added order fields to `OrderRequest` and Alpaca broker submission mapping for supported order types.
- Added order defaults in strategy config and dynamic limit/stop basis-point offsets.
- Expanded `trades.csv` with raw fill price, fill reason, order fields, remaining quantity, and fill bar OHLCV.
- Added execution simulator tests and next-bar-open backtest coverage.

## 2026-05-17 Order-Driven Backtest Refactor

- Added `qts.backtest.broker.SimulatedBroker` with order IDs, order status, latency, open-order quantities, partial-fill state, expiry, cancellation, and event history.
- Refactored `BacktestEngine` to submit orders to the simulated broker and consume fill events instead of managing pending orders internally.
- Kept fill-price assumptions in `qts.backtest.execution` and portfolio accounting in `qts.backtest.portfolio`.
- Added `orders.csv` and `order_events.csv` report artifacts.
- Added broker lifecycle tests and engine assertions for order IDs/status.
