# Alpaca Integration

Alpaca integration is isolated in two adapters:

- `qts.data.alpaca.AlpacaHistoricalDataClient`
- `qts.execution.alpaca_broker.AlpacaBrokerAdapter`

Credentials are loaded from environment variables:

```text
ALPACA_API_KEY_ID
ALPACA_API_SECRET_KEY
ALPACA_PAPER
ALPACA_DATA_FEED
```

## Historical Data

Use:

```bash
python scripts/download_data.py --config configs/backtest.yaml
```

The downloader normalizes Alpaca bars and writes local Parquet files.

## Paper Trading

Use:

```bash
python scripts/run_paper_trading.py --config configs/paper_trading.yaml --once
```

The default config uses paper mode and dry-run mode. The broker adapter supports account, positions, clock, submit order, cancel order, and order status.

The execution layer also provides `qts.execution.plan_orders_from_targets`, which converts broker-independent strategy target positions into market order requests using account equity, current quantities, latest prices, and max-position limits. The backtest portfolio uses this same planner, so target-to-order behavior stays aligned between research and future paper/live execution.

## Live Trading Readiness

Live trading is disabled by default. Before enabling live trading, add and validate:

- explicit live config flag
- kill switch
- max daily loss guard
- max position guard
- order confirmation mode
- monitoring and alerting
- operational checklist
