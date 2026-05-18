# Architecture

The system is a lightweight research-first trading platform with clean boundaries between data, signals, strategies, backtesting, risk, execution, ML, and reporting.

## Core Flow

1. Configuration is loaded from YAML and environment variables.
2. Historical bars are generated locally, loaded from local CSV/Parquet, or downloaded from Alpaca.
3. Feature functions produce deterministic reusable columns.
4. Signal providers produce normalized `TradingSignal` objects.
5. Strategies convert signals into broker-neutral `OrderRequest` objects.
6. Risk checks clip or reject order intents.
7. The active `BrokerAdapter` accepts or rejects orders.
8. Backtests use `BacktestBroker`, which handles status, latency, expiry, partial fills, and fill events.
9. The execution simulator prices backtest fills from OHLCV assumptions, slippage, and commissions.
10. The portfolio module applies `FillEvent` objects to cash, positions, average prices, and PnL.
11. Reports write orders, order events, trades, equity, metrics, and optional charts.

The mode-independent execution flow is:

```text
SignalProvider -> Strategy -> OrderRequest -> RiskManager -> BrokerAdapter -> OrderResult / FillEvent -> Portfolio / AccountLedger -> Reporting
```

## Important Boundary

A signal is a signal. Rule-based indicators and ML models both implement the same signal provider behavior and produce the same `TradingSignal` data model. The strategy and broker flow does not know or care whether an order intent came from a moving average, RSI, logistic regression, XGBoost, or a future reinforcement learning policy.

Strategies do not know whether they are running in backtest, Alpaca paper trading, or future live trading mode. They generate `OrderRequest` objects against a shared broker/account interface. Mode-specific behavior belongs in the broker adapter:

- `BacktestBroker`: simulated brokerage behavior and fill events.
- `AlpacaPaperBroker`: maps the same `OrderRequest` model to Alpaca paper trading APIs.
- `AlpacaLiveBroker`: disabled by default and blocked unless explicitly configured.

## Runtime Modes

- `backtest`: local deterministic simulation.
- `paper`: Alpaca paper trading adapter, live orders disabled by default through dry-run configuration.
- `live`: reserved for future use and blocked unless explicitly enabled.
- `research`: exploratory workflows using data, features, and ML modules.

## Design Choices

- Parquet is the default local store because it is simple, fast, and inspectable.
- Alpaca-specific code is isolated in `qts.data.alpaca` and `qts.execution.alpaca_broker`.
- Strategies are broker-independent.
- Risk management is shared between backtest and execution paths.
- Portfolio state changes only from `FillEvent` processing in backtests.
- No web dashboard, job scheduler, streaming bus, or heavyweight infrastructure is included in the initial version.
