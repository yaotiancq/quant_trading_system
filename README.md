# Quant Trading System

A lightweight, research-first quantitative trading research and execution platform built around Alpaca data and trading APIs.

The system is designed for fast strategy iteration, repeatable backtests, local historical data management, unified rule-based and machine-learning signals, and a clean path from backtesting to Alpaca paper trading. Live trading is intentionally disabled by default.

## What Is Included

- YAML configuration loading with environment-based Alpaca credentials.
- Local CSV and Parquet market data loading.
- Deterministic sample data generation.
- Configurable loaded-data timezone, defaulting to Pacific Time.
- Alpaca historical data downloader.
- Deterministic feature engineering.
- Unified signal interface for rule-based and ML signals.
- Moving average crossover, RSI mean reversion, and breakout rule-based signals.
- Baseline logistic regression ML model and ML signal provider.
- Strategy interface that converts signals into target positions.
- Bar-by-bar backtest engine with latency, slippage, commissions, cash, positions, trades, equity, and metrics.
- Alpaca broker adapter for paper trading and future guarded live trading.
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
python scripts/run_backtest.py --config configs/backtest.yaml
```

Outputs are written to `reports/backtests/`.
Each report also includes `summary.md` and `run_metadata.json` with the config snapshot and input data summary.
When charting is enabled, reports include `equity_curve.png` and `<SYMBOL>_diagnostics.png` with price action, indicators, volume, and buy/sell markers.

## Download Alpaca Historical Data

Set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in `.env`, update `configs/backtest.yaml`, then run:

```bash
python scripts/download_data.py --config configs/backtest.yaml
```

Data is stored as partitioned Parquet under `data/raw/source=alpaca/timeframe=<timeframe>/symbol=<symbol>/bars.parquet`.

## Train Baseline ML Model

```bash
python scripts/train_model.py --config configs/backtest.yaml --output models/baseline_logistic.joblib
```

The model uses deterministic technical features, future-return labels, a time-based split, and `joblib` persistence.

## Run ML Backtest

```bash
python scripts/run_ml_backtest.py --config configs/ml_backtest.yaml --model models/baseline_logistic.joblib
```

ML signals flow through the same `SignalDrivenStrategy`, risk manager, and backtest engine as rule-based signals.

## Run Paper Trading Dry-Run

```bash
python scripts/run_paper_trading.py --config configs/paper_trading.yaml --dry-run
```

The default paper config is `dry_run: true`. The command above validates configuration without opening an Alpaca connection or submitting orders. Use `--connect --once` when credentials are configured and you explicitly want to check Alpaca account/clock connectivity.

## Repository Structure

```text
configs/                 Example YAML configs
data/raw/                Local raw market data and sample CSV
data/processed/          Processed data and local artifacts
docs/                    System design documentation
scripts/                 CLI entry points
src/qts/                 Python package
tests/                   Pytest suite
```

## Known Limitations

- The paper trading loop is a safe dry-run/connectivity scaffold, not a full autonomous trading loop yet.
- Live trading is blocked unless explicitly enabled and should receive additional operational review.
- The first backtest engine supports market-order simulation, simple slippage, simple commissions, and bar-based latency.
- Second-level bars are supported by the data model and event loop when data is available. The current Alpaca stock-bar adapter supports SDK-exposed bar intervals; second-level Alpaca data should be added through local normalized bars or a future trade/quote aggregation adapter.
- The ML baseline is intentionally simple and should be treated as an example workflow, not a production model.
