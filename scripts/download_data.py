from __future__ import annotations

import argparse
from datetime import datetime, timezone

from qts.config.loader import load_app_config, load_env_settings
from qts.data.alpaca import AlpacaHistoricalDataClient
from qts.data.storage import ParquetDataStore
from qts.utils.logging import configure_logging, get_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Download historical bars from Alpaca into local Parquet storage.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--data-profile", default="alpaca")
    args = parser.parse_args()

    configure_logging()
    logger = get_logger(__name__)
    config = load_app_config(args.config, profile_overrides={"mode": "research", "data": args.data_profile})
    settings = load_env_settings()
    if not config.data.start or not config.data.end:
        raise ValueError("Data start and end dates are required for Alpaca downloads.")
    start = datetime.fromisoformat(config.data.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(config.data.end).replace(tzinfo=timezone.utc)
    client = AlpacaHistoricalDataClient(settings, feed=config.data.feed or settings.alpaca_data_feed)
    data = client.get_stock_bars(config.data.symbols, config.data.timeframe, start, end)
    store = ParquetDataStore(config.data.data_dir)
    for symbol in config.data.symbols:
        path = store.write_bars(data[data["symbol"] == symbol], symbol=symbol, timeframe=config.data.timeframe, source="alpaca")
        logger.info("Wrote %s", path)


if __name__ == "__main__":
    main()
