# Project State

Date: 2026-05-18

## Current Status

The project is a working lightweight research/backtesting MVP for local quantitative strategy research. It can generate deterministic local sample bars, load CSV or Parquet data, compute technical features, generate rule-based and ML signals through the same `TradingSignal` interface, run order-driven bar-by-bar backtests, write reports, train a baseline scikit-learn model, and validate Alpaca paper-trading configuration in dry-run mode.

## Completed Work

- Added deterministic sample data generation with CSV and partitioned Parquet output.
- Made the default backtest config local-first and credential-free.
- Added required Alpaca environment variable names with compatibility for older aliases.
- Expanded technical features for ML-ready research.
- Added breakout signals and strengthened signal combination behavior.
- Added order-level risk checks, session filters, max order notional, max quantity, and kill-switch flattening.
- Improved backtest order planning by accounting for pending latency-delayed orders.
- Replaced close-price-only fill logic with configurable OHLCV order simulation for market, limit, stop, stop-limit, and trailing-stop orders.
- Refactored backtesting to be order-driven through `BacktestBroker` / `SimulatedBroker`, with explicit order IDs, status transitions, latency, partial fills, expiry, cancellation, and order event logs.
- Refactored the architecture to use a shared `BrokerAdapter` contract across backtest, Alpaca paper trading, and future guarded live trading.
- Added canonical `OrderRequest`, `OrderSide`, `OrderType`, `OrderStatus`, and `FillEvent` models.
- Added `BacktestBroker` as the backtest implementation of the shared broker interface.
- Updated strategies to produce `OrderRequest` objects through `generate_orders(...)` instead of letting the backtest mutate positions from signals.
- Restricted portfolio accounting to public `FillEvent` processing through `Portfolio.apply_fill_event(...)`.
- Added `AlpacaPaperBroker` and a disabled-by-default `AlpacaLiveBroker` guard.
- Added strategy config order defaults and dynamic limit/stop price offsets.
- Updated diagnostic charts to show order submissions, buy/sell/short/cover fills, partial fills, and raw-vs-slipped fill prices.
- Tightened backtest correctness by splitting reversal targets into close/open legs, enforcing strict order-side semantics, adding liquidation-specific risk validation, path-aware stop-limit simulation, end-of-backtest order expiration, buying-power checks, disabled current-close fills, and timestamp-aware metric annualization.
- Added safe paper-trading dry-run behavior that does not require credentials or network access unless `--connect` is requested.
- Added summary report output.
- Added tests for validation, features, metrics, risk, signal combination, and existing core workflows.
- Added practical documentation and continuity files.

## Files Added Or Changed

Major added files include:

- `src/qts/backtest/broker.py`
- `src/qts/backtest/orders.py`
- `src/qts/backtest/fills.py`
- `src/qts/backtest/simulated_broker.py`
- `scripts/generate_sample_data.py`
- `src/qts/backtest/execution.py`
- `src/qts/execution/paper_loop.py`
- `src/qts/config/settings.py`
- `src/qts/data/local_store.py`
- `src/qts/data/alpaca_downloader.py`
- `src/qts/features/dataset.py`
- `src/qts/signals/combiner.py`
- `src/qts/signals/ml_signal.py`
- `src/qts/ml/dataset_builder.py`
- `src/qts/ml/model_store.py`
- `src/qts/ml/train.py`
- `docs/risk_management.md`
- `docs/cli_usage.md`
- `tests/test_features.py`
- `tests/test_metrics.py`
- `tests/test_risk.py`
- `tests/test_backtest_broker.py`
- `tests/test_broker_adapter_architecture.py`

Major changed areas include config loading, data validation, feature engineering, rule-based signals, signal combining, strategy order generation, risk management, backtest execution, broker adapters, reporting, configs, README, and user manual.

## Commands To Run

```bash
pip install -e ".[dev]"
python scripts/generate_sample_data.py
python scripts/run_backtest.py --config configs/backtest.yaml
python scripts/train_model.py --config configs/backtest.yaml
python scripts/run_paper_trading.py --config configs/paper_trading.yaml --dry-run
pytest
```

## Test Status

Last run in the repository virtual environment:

```text
.venv/bin/python -m pip install -e ".[dev]" could not complete in this sandbox because pip could not reach PyPI to install the `setuptools>=68` build dependency. Escalated network approval was requested twice and timed out. The existing virtual environment was still able to run the project and tests.
.venv/bin/python scripts/generate_sample_data.py passed.
.venv/bin/python scripts/run_backtest.py --config configs/backtest.yaml passed.
.venv/bin/python scripts/train_model.py --config configs/backtest.yaml passed.
.venv/bin/python scripts/run_paper_trading.py --config configs/paper_trading.yaml --dry-run passed without Alpaca credentials or network connection.
.venv/bin/python -m pytest
64 passed
```

Package created at `/tmp/quant_trading_system_order_driven.zip`. The archive excludes `.env`, `.git`, `.venv`, caches, egg-info, and Alpaca data partitions.

## Known Limitations

- Backtests are order-driven with an explicit shared-interface `BacktestBroker`, execution simulator, and portfolio accounting module.
- Backtest fills are OHLCV bar simulations with configurable latency, market fill price, slippage, commissions, partial fills, path-aware order-type behavior, and simple buying-power checks.
- Queue priority, spread dynamics, borrow availability, detailed margin rules, corporate actions, and exchange microstructure are not modeled.
- The paper-trading loop is a safe dry-run/connectivity scaffold. The Alpaca paper broker shares the same order interface, but autonomous recent-bar polling and order submission remain future work.
- Alpaca live trading is disabled by default and has not been tested with live credentials.
- Second-level bars are supported when normalized local data is available; this is not high-frequency trading infrastructure.
- The ML model is a baseline example and does not imply predictive edge or future profitability.

## Next Recommended Tasks

- Add a paper-trading strategy loop that pulls recent bars, generates `OrderRequest` objects, validates orders, and submits only in non-dry-run mode.
- Add broker-aware position reconciliation and buying-power checks.
- Add richer cost models and optional stop-loss/take-profit rules.
- Add walk-forward ML evaluation and model comparison reports.
- Add more multi-symbol test cases and portfolio-level attribution.
