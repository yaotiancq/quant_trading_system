from __future__ import annotations

import argparse
import time

from qts.config.loader import load_app_config, load_env_settings
from qts.execution.alpaca_broker import AlpacaBrokerAdapter
from qts.utils.logging import configure_logging, get_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Alpaca paper trading entry point.")
    parser.add_argument("--config", default="configs/paper_trading.yaml")
    parser.add_argument("--once", action="store_true", help="Check connectivity and exit.")
    args = parser.parse_args()

    configure_logging()
    logger = get_logger(__name__)
    config = load_app_config(args.config)
    if not config.execution.paper and not config.execution.live_trading_enabled:
        raise ValueError("Live trading is disabled by default and requires live_trading_enabled=true.")
    if config.execution.dry_run:
        logger.info("Dry-run mode is enabled. Orders will not be submitted.")
    settings = load_env_settings()
    broker = AlpacaBrokerAdapter(
        settings,
        paper=config.execution.paper,
        live_trading_enabled=config.execution.live_trading_enabled,
    )
    while True:
        clock = broker.get_clock()
        account = broker.get_account()
        logger.info("Clock=%s equity=%s buying_power=%s", clock, getattr(account, "equity", None), getattr(account, "buying_power", None))
        if args.once:
            break
        time.sleep(config.execution.poll_interval_seconds)


if __name__ == "__main__":
    main()

