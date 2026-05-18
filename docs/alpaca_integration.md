# Alpaca Integration

Alpaca integration is isolated in two adapters:

- `qts.data.alpaca.AlpacaHistoricalDataClient`
- `qts.execution.alpaca_broker.AlpacaBrokerAdapter`

Credentials are loaded from environment variables:

```text
ALPACA_API_KEY
ALPACA_SECRET_KEY
ALPACA_PAPER
ALPACA_DATA_FEED
```

The loader also accepts the older aliases `ALPACA_API_KEY_ID` and `ALPACA_API_SECRET_KEY` for compatibility. Do not put credentials in YAML files or source code.

## Historical Data

Use:

```bash
python scripts/download_data.py --config configs/backtest.yaml
```

The downloader normalizes Alpaca bars and writes local Parquet files.

## Paper Trading

Use:

```bash
python scripts/run_paper_trading.py --config configs/paper_trading.yaml --dry-run
```

The default config uses paper mode and dry-run mode. This validates the local configuration without opening a broker connection or submitting orders. To explicitly test Alpaca connectivity with credentials configured:

```bash
python scripts/run_paper_trading.py --config configs/paper_trading.yaml --dry-run --connect --once
```

The broker adapter supports account, positions, clock, submit order, cancel order, and order status. Dry-run mode never submits orders.

The broker-neutral `OrderRequest` model and Alpaca adapter support the installed Alpaca SDK order types:

- `market`
- `limit`
- `stop`
- `stop_limit`
- `trailing_stop`

Supported time-in-force values are `day`, `gtc`, `opg`, `cls`, `ioc`, and `fok`. Bracket/OCO/OTO order classes are represented on the request model for adapter compatibility, but full multi-leg backtest simulation is future work.

For equity backtests, the risk layer rejects unsupported combinations such as stop orders with `ioc`, or extended-hours market orders. Extended-hours simulation currently allows only limit orders with `day` or `gtc`, matching Alpaca's documented constraint.

The execution layer also provides `qts.execution.plan_orders_from_targets`, which converts broker-independent strategy target positions into market order requests using account equity, current quantities, latest prices, and max-position limits. The backtest portfolio uses this same planner, so target-to-order behavior stays aligned between research and future paper/live execution.

## Live Trading Readiness

Live trading is disabled by default. Before enabling live trading, add and validate:

- explicit live config flag
- kill switch
- max daily loss guard
- max position guard
- max order notional guard
- order confirmation mode
- monitoring and alerting
- operational checklist
