# User Manual

This manual explains how to install, configure, run, and extend the Quant Trading System.

## 1. Safety First

This project is for quantitative research and software development. Backtest results are simulated. Paper trading results are not live trading results. Live trading is disabled by default and should not be enabled until you have added operational safeguards, reviewed broker permissions, and accepted the financial risk.

Never store Alpaca API keys in source files. Use `.env`.

## 2. Installation

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env` only if you need Alpaca data downloads or paper trading:

```text
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_PAPER=true
ALPACA_DATA_FEED=iex
```

## 3. Project Layout

```text
configs/                 YAML run configurations
data/raw/                Local raw market data
data/processed/          Generated processed artifacts
docs/                    System documentation
scripts/                 Command-line entry points
src/qts/                 Python source package
tests/                   Automated tests
```

The most important source modules are:

```text
qts.data                 Data loading, validation, Alpaca download adapter, Parquet storage
qts.features             Deterministic feature engineering
qts.signals              Unified rule-based and ML signal interface
qts.strategies           Strategy wrappers that convert signals into OrderRequest objects
qts.backtest             Backtest broker, portfolio accounting, execution simulation, metrics
qts.risk                 Order validation and exposure limits
qts.ml                   Dataset creation, baseline model, ML signal provider
qts.execution            Broker adapter interface and Alpaca paper/live adapter guard
qts.reporting            CSV, JSON, and chart output
```

## 4. Configuration Files

Backtests and paper trading are controlled by YAML files in `configs/`.

Common sections:

```yaml
mode: backtest
data:
  data_dir: data/raw
  data_file: null
  source: local
  timeframe: 1Min
  timezone: America/Los_Angeles
  symbols: [SPY]
  start: "2024-01-02"
  end: "2024-01-05"
strategy:
  name: moving_average_crossover
  parameters:
    fast_window: 5
    slow_window: 20
    order_type: market
    time_in_force: day
risk:
  max_gross_exposure: 1.0
  max_portfolio_exposure: 1.0
  max_symbol_exposure: 1.0
  max_order_notional: 50000
  max_position_quantity: 1000
  max_position_qty: 1000
  allow_short: true
backtest:
  initial_cash: 100000
  slippage_bps: 2.0
  commission_bps: 0.0
  fixed_commission: 0.0
  latency_bars: 1
  latency_seconds: 0
  market_order_fill: next_open
  limit_fill_price: limit
  stop_fill_price: stop
  intrabar_price_path: open_high_low_close
  volume_participation_limit: 0.05
  allow_partial_fills: false
execution:
  mode: backtest
  broker: backtest
  market_order_fill: next_open
broker:
  provider: alpaca
  paper: true
  live_trading_enabled: false
  require_order_confirmation: true
```

Important assumptions such as slippage, commissions, latency, exposure limits, and starting cash should be changed in config rather than hard-coded into strategies.

`latency_bars` must be at least `1`. The engine assumes signals are generated after the current bar is known and orders fill no earlier than a later bar. This avoids same-bar close-to-close look-ahead behavior.

The default market-order simulation fills at the next eligible bar open, not the signal bar close. You can change `market_order_fill` to `next_close`, `next_vwap`, or `current_close` for sensitivity analysis. `current_close` is intentionally not the default because it can be optimistic.

Loaded timestamps default to Pacific Time through `timezone: America/Los_Angeles`. The aliases `PT`, `PST`, and `PDT` are accepted and normalized to `America/Los_Angeles`. Raw timestamps with an explicit timezone, such as `Z`/UTC Alpaca timestamps, are converted to the configured timezone. Naive timestamps are treated the same way pandas treats them during UTC normalization, so prefer timezone-aware raw data.

## 5. Run Tests

```bash
pytest
```

Use this after every change to strategy, accounting, data, or ML code.

## 6. Generate Sample Data

The default local workflow uses deterministic sample bars:

```bash
python scripts/generate_sample_data.py
```

This writes `data/raw/sample_bars.csv` and local Parquet partitions under `data/raw/source=local/`.

## 7. Run a Rule-Based Backtest

The repository includes a deterministic sample CSV at `data/raw/sample_bars.csv`.

```bash
python scripts/run_backtest.py --config configs/backtest.yaml
```

Outputs:

```text
reports/backtests/equity_curve.csv
reports/backtests/trades.csv
reports/backtests/orders.csv
reports/backtests/order_events.csv
reports/backtests/metrics.json
reports/backtests/run_metadata.json
reports/backtests/summary.md
reports/backtests/equity_curve.png
reports/backtests/SPY_diagnostics.png
```

Use `--no-chart` to skip chart generation:

```bash
python scripts/run_backtest.py --config configs/backtest.yaml --no-chart
```

`run_metadata.json` contains the run timestamp, QTS version, full config snapshot, data source, symbol list, row count, and data start/end timestamps. Keep it with metrics and trades when comparing strategy runs.

`<SYMBOL>_diagnostics.png` plots candlestick price action with buy, sell, short, and cover fill markers, optional order-submission markers, raw-vs-slipped fill hints, moving averages, VWAP, Bollinger Bands, RSI, MACD, and volume panels. Use it for quick visual inspection before deeper quantitative analysis.

## 7.1. Use a Custom Local Data File

For fast research, point a config directly at a CSV or Parquet file:

```yaml
data:
  data_file: data/raw/my_experiment.csv
  source: local_experiment
  timeframe: 1Min
  timezone: America/Los_Angeles
  symbols: [SPY]
  start: "2024-01-02"
  end: "2024-01-31"
```

The file must contain at least:

```text
timestamp,symbol,open,high,low,close,volume
```

Optional columns include `trade_count`, `vwap`, `timeframe`, and `source`. When `data_file` is set, the config `source` and `timeframe` are applied to the loaded rows so provenance remains explicit.

## 8. Download Alpaca Historical Data

Set credentials in `.env`, then edit the `data` section of a config:

```yaml
data:
  data_dir: data/raw
  source: alpaca
  timeframe: 1Min
  symbols: [SPY, AAPL]
  start: "2024-01-02"
  end: "2024-01-31"
  feed: iex
```

Run:

```bash
python scripts/download_data.py --config configs/backtest.yaml
```

Stored files use this layout:

```text
data/raw/source=alpaca/timeframe=1Min/symbol=SPY/bars.parquet
```

For backtesting downloaded data, keep `source: alpaca` in the config so the loader reads from the Alpaca Parquet partition.

## 9. Train the Baseline ML Model

The baseline model uses deterministic technical features and a time-based train/test split.

```bash
python scripts/train_model.py \
  --config configs/backtest.yaml \
  --output models/baseline_logistic.joblib
```

Useful options:

```bash
python scripts/train_model.py \
  --config configs/backtest.yaml \
  --output models/baseline_logistic.joblib \
  --horizon 1 \
  --threshold 0.0 \
  --train-fraction 0.7
```

Do not use random train/test splits for market data research unless you have a specific reason and understand the leakage risk.

## 10. Run an ML Backtest

After training a model:

```bash
python scripts/run_ml_backtest.py --config configs/ml_backtest.yaml
```

You can override the model path:

```bash
python scripts/run_ml_backtest.py \
  --config configs/ml_backtest.yaml \
  --model models/baseline_logistic.joblib
```

The ML strategy uses the same signal interface, risk manager, portfolio accounting, and backtest engine as rule-based strategies.

Rule-based and ML signals both use the same `TradingSignal` schema. Each signal also carries structured provenance:

- `source_name`: provider name
- `source_type`: `RULE_BASED`, `ML`, or `COMBINED`
- `model_version`: populated for ML providers
- `feature_set`: features used by the provider
- `confidence_metadata`: how confidence was produced

This provenance is preserved into order metadata and backtest trade logs for attribution and risk review.

## 11. Run Paper Trading Dry-Run

Paper trading is intentionally conservative. The default config uses `dry_run: true`.

```bash
python scripts/run_paper_trading.py --config configs/paper_trading.yaml --dry-run
```

This validates paper-trading configuration without opening an Alpaca connection or submitting orders. To explicitly check Alpaca account and clock access after credentials are configured:

```bash
python scripts/run_paper_trading.py --config configs/paper_trading.yaml --dry-run --connect --once
```

This does not run a full autonomous trading loop yet.

The shared execution helper `qts.execution.plan_orders_from_targets` converts signal targets into `OrderRequest` objects from account equity, current positions, pending orders, and latest prices. `SignalDrivenStrategy.generate_orders` uses the same broker-neutral path whether the broker is `BacktestBroker`, `AlpacaPaperBroker`, or a future guarded live broker.

## 12. Create a New Rule-Based Signal

Add a class in `src/qts/signals/rule_based.py` or a new module. It should implement:

```python
def generate(self, history: pd.DataFrame, timestamp: pd.Timestamp) -> list[TradingSignal]:
    ...
```

Rules:

- Use only `history` at or before `timestamp`.
- Return `HOLD` when there is not enough data.
- Set `target_position` to a signed portfolio fraction when possible.
- Add provider details to `metadata`.

Then register it in `create_strategy_from_config` in `src/qts/strategies/signal_strategy.py`.

## 13. Create a New ML Signal

ML models should not submit orders. They should produce predictions that are converted into `TradingSignal` objects.

Typical workflow:

1. Add deterministic features in `qts.features`.
2. Build labels in `qts.ml.dataset`.
3. Train and save a model in `qts.ml.model` or a new model module.
4. Create a signal provider that converts predictions to `LONG`, `SHORT`, `FLAT`, or `HOLD`.
5. Register the provider in the strategy factory.
6. Backtest it through the existing engine.

## 14. Interpreting Backtest Output

Key files:

- `equity_curve.csv`: cash, market value, equity, and exposure over time.
- `trades.csv`: simulated fills, position after fill, closed quantity, realized PnL, holding period, and signal provenance.
- `orders.csv`: final simulated broker state for every submitted order.
- `order_events.csv`: status transition history for submitted, accepted, partial fill, fill, cancel, and expiry events.
- `metrics.json`: summary metrics.
- `run_metadata.json`: config snapshot and input data summary for reproducibility.
- `<SYMBOL>_diagnostics.png`: price, indicator, volume, and trade-marker diagnostics.

Key metrics:

- `total_return`: total simulated return over the test period.
- `max_drawdown`: worst peak-to-trough equity decline.
- `sharpe_ratio`: annualized return volatility ratio based on configured periods.
- `win_rate`: percent of closed trades with positive realized PnL.
- `profit_factor`: gross profit divided by gross loss.
- `exposure_time`: fraction of bars with non-zero exposure.

Metrics are only as reliable as the data and assumptions.

The equity curve also includes:

- `daily_pnl`: current session PnL versus session-start equity.
- `risk_halted`: whether the max daily loss guard has halted new entries and is forcing positions flat.

The max daily loss guard resets at the next UTC date in the historical data.

### Order Simulation Fields

`trades.csv` includes execution simulation details:

- `order_id`
- `order_type` and `time_in_force`
- `requested_quantity`, `quantity`, and `remaining_quantity`
- `limit_price`, `stop_price`, `trail_price`, and `trail_percent`
- `raw_fill_price`, before slippage
- `fill_price`, after slippage
- `fill_reason`
- `fill_bar_open`, `fill_bar_high`, `fill_bar_low`, `fill_bar_close`, `fill_bar_vwap`, and `fill_bar_volume`

Supported order types are `market`, `limit`, `stop`, `stop_limit`, and `trailing_stop`. Supported time-in-force values are `day`, `gtc`, `opg`, `cls`, `ioc`, and `fok`.

The backtest is now order-driven. The strategy produces intent, the order planner creates `OrderRequest` objects, the risk manager validates them, the simulated broker owns order status and latency, the execution simulator decides fills from bar data, and the portfolio module applies fills to cash and positions.

To experiment with a limit order generated from the signal bar close:

```yaml
strategy:
  name: moving_average_crossover
  parameters:
    fast_window: 5
    slow_window: 20
    target_notional_fraction: 0.5
    order_type: limit
    time_in_force: day
    limit_price_offset_bps: 5
```

For a buy order, `limit_price_offset_bps: 5` places the limit 5 basis points below the reference close. For a sell order, it places the limit 5 basis points above the reference close. Stop offsets work in the opposite direction.

## 15. Charting And Visual Diagnostics

The reporting layer includes lightweight charting for strategy inspection:

```python
from qts.reporting import plot_strategy_diagnostics, plot_trade_window

plot_strategy_diagnostics(
    bars=data,
    trades=result.trades,
    output_path="reports/backtests/SPY_diagnostics.png",
    symbol="SPY",
    orders=result.orders,
)

plot_trade_window(
    bars=data,
    trades=result.trades,
    trade_index=0,
    output_path="reports/backtests/SPY_trade_0.png",
    orders=result.orders,
)
```

Supported diagnostics:

- candlestick-style OHLC price panel
- buy, sell, short, and cover markers from backtest fills
- order-submission markers when `orders` is provided
- raw fill and slipped fill visualization when those prices differ
- moving averages
- VWAP
- Bollinger Bands
- RSI
- MACD
- volume
- custom lower panels for additional columns

To add a custom model output or indicator, add it as a column to the bars DataFrame and pass the column name in `oscillator_panels`.

## 16. Common Issues

If `pytest` is not found:

```bash
pip install -e ".[dev]"
```

If Alpaca credentials are missing:

```text
ValueError: Alpaca API credentials are required in environment variables.
```

Add credentials to `.env`.

If no data is found:

```text
FileNotFoundError: No local data found...
```

Check `data_dir`, `source`, `timeframe`, and `symbols` in the config.

If an ML backtest cannot find the model:

```bash
python scripts/train_model.py --config configs/backtest.yaml --output models/baseline_logistic.joblib
```

Then rerun the ML backtest.

## 17. Current Limitations

- Backtest fills are OHLCV bar simulations with configurable latency, slippage, order-type behavior, and partial-fill assumptions.
- Paper trading is a safe connectivity scaffold, not a complete automated trading daemon.
- Live trading is intentionally disabled and requires additional controls.
- Second-level local bars are supported by the model and engine, but the current Alpaca stock-bar adapter depends on SDK-supported bar intervals.
- The baseline ML model is an example workflow, not a production prediction system.
