# Architecture

The system is a lightweight research-first trading platform with clean boundaries between data, signals, strategies, backtesting, risk, execution, ML, and reporting.

## Core Flow

1. Configuration is loaded from YAML and environment variables.
2. Historical bars are generated locally, loaded from local CSV/Parquet, or downloaded from Alpaca.
3. Feature functions produce deterministic reusable columns.
4. Signal providers produce normalized `TradingSignal` objects.
5. Strategies convert signals into target portfolio fractions.
6. Risk checks clip or reject target positions and order intents.
7. The backtest engine simulates delayed market fills, costs, cash, positions, trades, and equity.
8. Reports write trades, equity, metrics, and optional charts.

## Important Boundary

A signal is a signal. Rule-based indicators and ML models both implement the same signal provider behavior and produce the same `TradingSignal` data model. The backtest engine does not know or care whether a target came from a moving average, RSI, logistic regression, XGBoost, or a future reinforcement learning policy.

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
- No web dashboard, job scheduler, streaming bus, or heavyweight infrastructure is included in the initial version.
