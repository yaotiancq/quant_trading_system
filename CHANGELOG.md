# Changelog

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
