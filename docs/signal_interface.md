# Signal Interface

All signal providers return `TradingSignal` objects:

| Field | Description |
| --- | --- |
| `timestamp` | Signal timestamp |
| `symbol` | Target symbol |
| `signal_type` | `RULE_BASED`, `ML`, or `COMBINED` |
| `direction` | `LONG`, `SHORT`, `FLAT`, or `HOLD` |
| `strength` | Normalized signal strength from 0 to 1 |
| `confidence` | Normalized confidence from 0 to 1 |
| `target_position` | Optional signed portfolio target fraction |
| `provenance` | Structured source attribution |
| `confidence_metadata` | Explanation of how confidence was produced |
| `metadata` | Provider-specific details |

`provenance` contains:

| Field | Description |
| --- | --- |
| `source_name` | Provider name, such as `moving_average_crossover` or `baseline_ml` |
| `source_type` | `RULE_BASED`, `ML`, or `COMBINED` |
| `model_version` | Optional model version for ML providers |
| `feature_set` | Feature names used by the signal provider |

Rule-based and ML signal providers share the same interface:

```python
signals = provider.generate(history, timestamp)
```

The `history` frame must contain only bars available at or before `timestamp`. Providers should emit `HOLD` when there is insufficient history.

Strategies consume signals and produce broker-neutral `OrderRequest` objects. Backtesting and execution consume strategy outputs, not provider-specific model details.

Implemented providers include moving average crossover, RSI mean reversion, breakout, and the baseline ML provider. `WeightedSignalCombiner` supports equal-weight and confidence-weighted combinations and resolves offsetting LONG/SHORT conflicts to FLAT by default.

Order behavior is intentionally separate from signal behavior. Strategy config can attach broker-neutral order defaults such as `order_type`, `time_in_force`, `limit_price_offset_bps`, or `stop_price_offset_bps`. The strategy uses the shared order planner to turn signal targets, account equity, current positions, pending orders, and latest prices into explicit `OrderRequest` objects. In backtests, those requests are submitted to `BacktestBroker`, which owns order status and fill events before the portfolio is updated. In Alpaca paper trading, the same requests are submitted through `AlpacaPaperBroker`.

Signal provenance is preserved as the signal moves into strategy order metadata, risk validation, broker submission, and backtest trade logs. Order metadata and `trades.csv` include fields such as:

- `signal_source_name`
- `signal_source_type`
- `signal_model_version`
- `signal_feature_set`
- `signal_confidence`
- `signal_confidence_metadata`
- `signal_snapshot`

This allows research attribution and later monitoring without making the portfolio, risk, or execution layers know the internal details of any specific signal provider.
