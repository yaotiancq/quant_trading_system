from __future__ import annotations

import argparse

from qts.config.loader import load_app_config, load_env_settings
from qts.execution.paper_loop import run_paper_loop
from qts.utils.logging import configure_logging, get_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Alpaca paper trading entry point.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--data-profile", default="alpaca")
    parser.add_argument("--strategy-profile", default=None)
    parser.add_argument("--risk-profile", default="paper")
    parser.add_argument("--execution-profile", default="paper")
    parser.add_argument("--broker-profile", default="alpaca_paper")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration without submitting orders.")
    parser.add_argument("--connect", action="store_true", help="Open an Alpaca connection during dry-run.")
    parser.add_argument("--once", action="store_true", help="Run one broker polling iteration when connected.")
    parser.add_argument("--iterations", type=int, default=None, help="Maximum broker polling iterations when connected.")
    args = parser.parse_args()

    configure_logging()
    logger = get_logger(__name__)
    config = load_app_config(
        args.config,
        profile_overrides={
            "mode": "paper",
            "data": args.data_profile,
            "strategy": args.strategy_profile,
            "risk": args.risk_profile,
            "execution": args.execution_profile,
            "broker": args.broker_profile,
        },
    )
    settings = load_env_settings()
    result = run_paper_loop(
        config,
        settings,
        dry_run=args.dry_run or config.execution.dry_run,
        connect=args.connect,
        iterations=1 if args.once else args.iterations,
    )
    logger.info("Paper trading entry point finished: %s", result)


if __name__ == "__main__":
    main()
