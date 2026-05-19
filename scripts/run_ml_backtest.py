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
    parser = argparse.ArgumentParser(description="Backtest a saved ML signal model.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--data-profile", default=None)
    parser.add_argument("--strategy-profile", default="baseline_ml")
    parser.add_argument("--risk-profile", default=None)
    parser.add_argument("--backtest-profile", default="ml")
    parser.add_argument("--execution-profile", default=None)
    parser.add_argument("--broker-profile", default=None)
    parser.add_argument("--model", default=None, help="Override strategy.parameters.model_path.")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--long-threshold", type=float, default=0.55)
    parser.add_argument("--short-threshold", type=float, default=0.45)
    parser.add_argument("--target-fraction", type=float, default=0.95)
    parser.add_argument("--no-chart", action="store_true")
    args = parser.parse_args()

    configure_logging()
    logger = get_logger(__name__)
    config = load_app_config(
        args.config,
        profile_overrides={
            "mode": "backtest",
            "data": args.data_profile,
            "strategy": args.strategy_profile,
            "risk": args.risk_profile,
            "backtest": args.backtest_profile,
            "execution": args.execution_profile,
            "broker": args.broker_profile,
        },
    )
    if args.model:
        config.strategy.parameters["model_path"] = args.model
    config.strategy.parameters["long_threshold"] = args.long_threshold
    config.strategy.parameters["short_threshold"] = args.short_threshold
    config.strategy.parameters["target_notional_fraction"] = args.target_fraction
    data = load_market_data(config.data)
    strategy = create_strategy_from_config(config.strategy)
    engine = BacktestEngine(config.backtest, strategy, RiskManager(config.risk))
    result = engine.run(data)
    metadata = build_run_metadata(config, data, run_type="ml_backtest")
    output_dir = args.output_dir or config.backtest.output_dir
    write_backtest_report(result, output_dir, make_chart=not args.no_chart, metadata=metadata, market_data=data)
    logger.info("ML backtest complete. Metrics:\n%s", json.dumps(result.metrics, indent=2))


if __name__ == "__main__":
    main()
