from __future__ import annotations

import argparse
import json

from qts.backtest.engine import BacktestEngine
from qts.config.loader import load_app_config
from qts.data.loader import load_market_data
from qts.reporting.reports import build_run_metadata, write_backtest_report
from qts.risk.manager import RiskManager
from qts.strategies.signal_strategy import create_strategy_from_config
from qts.utils.logging import configure_logging, get_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a bar-by-bar backtest.")
    parser.add_argument("--config", default="configs/backtest.yaml")
    parser.add_argument("--no-chart", action="store_true")
    args = parser.parse_args()

    configure_logging()
    logger = get_logger(__name__)
    config = load_app_config(args.config)
    data = load_market_data(config.data)
    strategy = create_strategy_from_config(config.strategy)
    engine = BacktestEngine(config.backtest, strategy, RiskManager(config.risk))
    result = engine.run(data)
    metadata = build_run_metadata(config, data, run_type="rule_based_backtest")
    write_backtest_report(result, config.backtest.output_dir, make_chart=not args.no_chart, metadata=metadata, market_data=data)
    logger.info("Backtest complete. Metrics:\n%s", json.dumps(result.metrics, indent=2))


if __name__ == "__main__":
    main()
