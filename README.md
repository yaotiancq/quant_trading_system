# Quant Trading System

A lightweight, research-first quantitative trading research and execution platform built around Alpaca data and trading APIs.

The system is designed for fast strategy iteration, repeatable backtests, local historical data management, unified rule-based and machine-learning signals, and a clean path from backtesting to Alpaca paper trading. Live trading is intentionally disabled by default.

## What Is Included

- Single-file YAML configuration with mode/profile selection and environment-based Alpaca credentials.
- Local CSV and Parquet market data loading.
- Deterministic sample data generation.
- Configurable loaded-data timezone, defaulting to Pacific Time.
- Alpaca historical data downloader.
- Deterministic feature engineering.
- Unified signal interface for rule-based and ML signals.
- Moving average crossover, RSI mean reversion, and breakout rule-based signals.
- Baseline logistic regression ML model and ML signal provider.
- Strategy interface that converts signals into broker-neutral `OrderRequest` objects through the shared order planner.
- Order-driven bar-by-bar backtest engine with simulated broker order status, latency, fills, slippage, commissions, cash, positions, trades, equity, and metrics.
- Shared `BrokerAdapter` interface with a backtest broker, Alpaca paper broker, and guarded disabled live broker.
- Lightweight reporting to CSV, JSON, and optional equity chart.
- Tests for config, data loading, validation, features, signals, risk, metrics, order planning, charts, and backtest behavior.

For detailed operating instructions, see [docs/user_manual.md](docs/user_manual.md).

## Financial Safety

This project is for research and software development. Backtest results are not evidence of future live performance. Paper trading results and live trading results should be evaluated separately. Live trading requires explicit configuration and additional operational controls.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Fill `.env` with Alpaca credentials only when using Alpaca data or paper trading.

The project uses one config file, `configs/config.yaml`. Choose active defaults in its `runtime` section or pass CLI profile overrides such as `--strategy-profile baseline_ml`, `--data-profile alpaca`, or `--risk-profile paper`.

## Generate Sample Data

```bash
python scripts/generate_sample_data.py
```

This writes deterministic local bars to `data/raw/sample_bars.csv` and partitioned Parquet under `data/raw/source=local/`. No Alpaca credentials are required.

## Run Tests

```bash
pytest
```

## Run Example Backtest

```bash
python scripts/run_backtest.py --config configs/config.yaml
```

Outputs are written to `reports/backtests/`.
Each report also includes `orders.csv`, `order_events.csv`, `summary.md`, and `run_metadata.json` with the config snapshot and input data summary.
When charting is enabled, reports include `equity_curve.png` and `<SYMBOL>_diagnostics.png` with price action, indicators, volume, order-submission markers, and buy/sell/short/cover fill markers.

## Download Alpaca Historical Data

Set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in `.env`, update the `profiles.data.alpaca` section in `configs/config.yaml`, then run:

```bash
python scripts/download_data.py --config configs/config.yaml
```

Data is stored as partitioned Parquet under `data/raw/source=alpaca/timeframe=<timeframe>/symbol=<symbol>/bars.parquet`.

## Train Baseline ML Model

```bash
python scripts/train_model.py --config configs/config.yaml --output models/baseline_logistic.joblib
```

The model uses deterministic technical features, future-return labels, a time-based split, and `joblib` persistence.

## Run ML Backtest

```bash
python scripts/run_ml_backtest.py --config configs/config.yaml --model models/baseline_logistic.joblib
```

ML signals flow through the same `SignalDrivenStrategy`, risk manager, and backtest engine as rule-based signals.

## Run Paper Trading Dry-Run

```bash
python scripts/run_paper_trading.py --config configs/config.yaml --dry-run
```

The paper execution profile is `dry_run: true`. The command above validates configuration without opening an Alpaca connection or submitting orders. Use `--connect --once` when credentials are configured and you explicitly want to check Alpaca account/clock connectivity.

## Execution Architecture

Strategies are mode-independent. The shared flow is:

```text
SignalProvider -> Strategy -> OrderRequest -> RiskManager -> BrokerAdapter -> FillEvent -> Portfolio -> Reporting
```

Backtests use `BacktestBroker` and `BarExecutionSimulator`; Alpaca paper trading uses `AlpacaPaperBroker`; future live trading uses the same interface but remains disabled unless explicitly configured.

## Repository Structure

```text
configs/                 Unified YAML config
data/raw/                Local raw market data and sample CSV
data/processed/          Processed data and local artifacts
docs/                    System design documentation
scripts/                 CLI entry points
src/qts/                 Python package
tests/                   Pytest suite
```

## Known Limitations

- The paper trading loop is a safe dry-run/connectivity scaffold. The broker adapter and strategy order path are shared, but continuous Alpaca bar polling and autonomous submission are intentionally not enabled by default.
- Live trading is blocked unless explicitly enabled and should receive additional operational review.
- The backtest engine uses OHLCV bar execution assumptions for supported order types, but it still does not model queue position, spread dynamics, borrow availability, or full market microstructure.
- Second-level bars are supported by the data model and event loop when data is available. The current Alpaca stock-bar adapter supports SDK-exposed bar intervals; second-level Alpaca data should be added through local normalized bars or a future trade/quote aggregation adapter.
- The ML baseline is intentionally simple and should be treated as an example workflow, not a production model.
