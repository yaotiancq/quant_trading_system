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
