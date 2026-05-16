from __future__ import annotations

from pathlib import Path

import pandas as pd

from qts.config.models import DataConfig
from qts.data.storage import ParquetDataStore
from qts.data.validation import normalize_market_data, parse_timestamp_bound


def load_market_data(config: DataConfig) -> pd.DataFrame:
    if config.data_file:
        path = Path(config.data_file)
        if not path.exists():
            raise FileNotFoundError(f"Configured data_file does not exist: {path}")
        if path.suffix.lower() == ".parquet":
            data = pd.read_parquet(path)
        else:
            data = pd.read_csv(path)
        normalized = normalize_market_data(
            data,
            timeframe=config.timeframe,
            source=config.source,
            timezone=config.timezone,
        )
        normalized["timeframe"] = config.timeframe
        normalized["source"] = config.source
        return _filter_loaded_data(normalized, config)

    data_dir = Path(config.data_dir)
    if config.source == "local":
        sample = data_dir / "sample_bars.csv"
        if sample.exists():
            data = pd.read_csv(sample)
            normalized = normalize_market_data(
                data,
                timeframe=config.timeframe,
                source="local",
                timezone=config.timezone,
            )
            return _filter_loaded_data(normalized, config)
    return ParquetDataStore(data_dir).read_bars(
        symbols=config.symbols,
        timeframe=config.timeframe,
        source=None if config.source == "local" else config.source,
        start=config.start,
        end=config.end,
        timezone=config.timezone,
    )


def _filter_loaded_data(data: pd.DataFrame, config: DataConfig) -> pd.DataFrame:
    if config.symbols:
        data = data[data["symbol"].isin(config.symbols)]
    if config.start:
        data = data[data["timestamp"] >= parse_timestamp_bound(config.start, config.timezone)]
    if config.end:
        data = data[data["timestamp"] <= parse_timestamp_bound(config.end, config.timezone)]
    return data.reset_index(drop=True)
