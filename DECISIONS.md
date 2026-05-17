# Decisions

Date: 2026-05-17

## Architecture Decisions

- Keep the project as a lightweight Python package with CLI scripts. No web dashboard, scheduler, queue, or distributed infrastructure is included.
- Keep strategies broker-independent. Strategies generate target positions; backtests and broker adapters handle execution details.
- Treat rule-based and ML signals as equal first-class providers through the `TradingSignal` interface.
- Keep Alpaca-specific code isolated in data and execution adapters.

## Storage Decisions

- Use local Parquet as the default durable research store.
- Keep CSV loading as a simple fallback and use `data/raw/sample_bars.csv` for the default local demo.
- Store partitioned bars by `source`, `timeframe`, and `symbol`.

## Backtest Assumptions

- Signals are generated after the current bar is known.
- Market orders fill no earlier than a later bar based on `latency_bars`.
- Fills use the eligible bar close adjusted by basis-point slippage and per-share commission.
- Pending delayed orders are counted when planning new target deltas.
- Backtest results are simulations and are not evidence of future profitability.

## Risk Assumptions

- Risk controls operate before simulated or paper-trading order submission.
- Target controls cap gross exposure, per-symbol exposure, and position notional.
- Order controls cap single-order notional and quantity.
- The daily loss guard halts new entries and targets open positions flat in backtests.
- The kill switch blocks new orders and forces flat targets in backtests.

## ML Assumptions

- The baseline model is logistic regression with deterministic technical features.
- Labels use future returns, while features use only information available at or before each timestamp.
- Train/test splitting is time-based, not random.
- ML models never place trades directly; they produce predictions or standardized signals only.

## Alpaca Assumptions

- Alpaca credentials are loaded only from environment variables.
- Required names are `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_PAPER`, and `ALPACA_DATA_FEED`; older key aliases are accepted for compatibility.
- Paper dry-run validates local configuration without opening a broker connection unless `--connect` is explicitly provided.
- Live trading remains disabled by default and requires explicit config, order confirmation, kill switch, max loss, max position, and max order guards.
