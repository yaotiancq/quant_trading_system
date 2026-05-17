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
python scripts/run_backtest.py --config configs/backtest.yaml
```

Train the baseline ML model:

```bash
python scripts/train_model.py --config configs/backtest.yaml
```

Run an ML backtest after training:

```bash
python scripts/run_ml_backtest.py --config configs/ml_backtest.yaml
```

Download Alpaca historical data after setting `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`:

```bash
python scripts/download_data.py --config configs/backtest.yaml
```

Validate paper-trading configuration without credentials, network access, or order submission:

```bash
python scripts/run_paper_trading.py --config configs/paper_trading.yaml --dry-run
```

Explicitly check Alpaca paper connectivity when credentials are configured:

```bash
python scripts/run_paper_trading.py --config configs/paper_trading.yaml --dry-run --connect --once
```

Run tests:

```bash
pytest
```
