# CLI Usage

Install dependencies:

```bash
pip install -e ".[dev]"
```

Generate deterministic local sample data:

```bash
python scripts/generate_sample_data.py
```

Run a local rule-based backtest:

```bash
python scripts/run_backtest.py --config configs/config.yaml
```

Use a different profile from the same config file:

```bash
python scripts/run_backtest.py --config configs/config.yaml --strategy-profile rsi_mean_reversion
```

Train the baseline ML model:

```bash
python scripts/train_model.py --config configs/config.yaml
```

Run an ML backtest after training:

```bash
python scripts/run_ml_backtest.py --config configs/config.yaml
```

This automatically selects the `baseline_ml` strategy profile and the `ml` backtest output profile unless you override them.

Download Alpaca historical data after setting `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`:

```bash
python scripts/download_data.py --config configs/config.yaml
```

Validate paper-trading configuration without credentials, network access, or order submission:

```bash
python scripts/run_paper_trading.py --config configs/config.yaml --dry-run
```

Explicitly check Alpaca paper connectivity when credentials are configured:

```bash
python scripts/run_paper_trading.py --config configs/config.yaml --dry-run --connect --once
```

Run tests:

```bash
pytest
```

All scripts read `configs/config.yaml` by default. The file contains named profiles for local sample data, Alpaca data, rule-based strategies, ML strategies, research risk, paper risk, backtest execution, paper execution, and guarded live readiness.
