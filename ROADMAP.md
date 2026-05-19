# Roadmap

## Completed

- Local sample data generation.
- Local CSV and partitioned Parquet loading.
- Data validation for required schema and OHLCV consistency.
- Deterministic technical features and ML-ready matrix generation.
- Unified signal interface for rule-based and ML providers.
- Moving average, RSI, breakout, ML, and combined signals.
- Signal-driven strategy wrapper.
- Bar-by-bar backtest engine with cash, positions, realized/unrealized PnL, latency, slippage, commissions, trade logs, equity curves, and metrics.
- OHLCV order execution simulator for market, limit, stop, stop-limit, and trailing-stop orders.
- Simulated backtest broker with order IDs, order status, latency, partial fills, expiry, cancellation, and order event logs.
- Shared `BrokerAdapter` architecture for backtest, Alpaca paper trading, and future guarded live trading.
- Canonical `OrderRequest` and `FillEvent` models shared by strategies, risk, brokers, execution simulation, and portfolio accounting.
- Strategy `generate_orders(...)` flow that keeps strategy logic mode-independent.
- Disabled-by-default `AlpacaLiveBroker` guard.
- Configurable market fill prices, intrabar path assumptions, and partial fills.
- Shared order planner and risk manager.
- Single-file profile-based configuration for backtesting, ML backtesting, Alpaca downloads, paper trading, and guarded live readiness.
- Alpaca historical downloader and isolated broker adapter.
- Safe paper-trading dry-run command.
- Reports with CSV, JSON, markdown summary, and optional charts.
- Core pytest coverage.

## Remaining MVP Hardening

- Add more multi-symbol portfolio tests.
- Add configurable borrow/margin assumptions for short positions.
- Add stronger trade attribution and per-symbol performance summaries.
- Add data calendar/session helpers for holidays and early closes.
- Add paper-trading loop order planning from recent Alpaca bars in dry-run first.
- Add broker/account reconciliation tests around live Alpaca paper responses.

## Future Enhancements

- Walk-forward model evaluation and model registry metadata.
- Additional ML models behind the same signal interface.
- More realistic fill models and spread-aware costs.
- Position reconciliation against broker state.
- Operational monitoring and alerting before any live-trading consideration.
- Live trading checklist and manual confirmation workflow.
