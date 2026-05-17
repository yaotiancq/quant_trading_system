# Data Model

Market bars use a normalized tabular schema:

| Column | Description |
| --- | --- |
| `timestamp` | Timezone-aware timestamp for the bar |
| `symbol` | Tradable symbol |
| `open` | Open price |
| `high` | High price |
| `low` | Low price |
| `close` | Close price |
| `volume` | Bar volume |
| `trade_count` | Optional trade count |
| `vwap` | Optional VWAP |
| `timeframe` | Bar timeframe such as `1Sec`, `1Min`, `1Day` |
| `source` | Data source such as `local` or `alpaca` |

Local Alpaca bars are stored as:

```text
data/raw/source=alpaca/timeframe=1Min/symbol=SPY/bars.parquet
```

Local generated sample bars use the same partition pattern with `source=local`. The CSV fallback used by the default backtest config is `data/raw/sample_bars.csv`.

Validation checks required columns, non-negative volume, and consistent OHLC ranges where `high >= max(open, close)` and `low <= min(open, close)`.

The loader supports second-level bars when available by using `timeframe: 1Sec`. Backtests operate over whatever timestamps are present, so second-level data flows through the same bar-by-bar engine. The installed Alpaca stock-bar SDK exposes minute, hour, and day bar constants; second-level Alpaca support should be added through local normalized second bars or a future trade/quote aggregation adapter.

Raw timestamps are normalized as timezone-aware timestamps. By default, the loader converts them to `America/Los_Angeles` through `data.timezone`; use `timezone: UTC` in config if you prefer UTC in research outputs. All data should be sorted by `timestamp` and `symbol`. Feature generation and signal generation must only use data at or before the current timestamp.
