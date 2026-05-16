from __future__ import annotations

from pathlib import Path

import pandas as pd

from qts.data.validation import normalize_market_data, parse_timestamp_bound


class ParquetDataStore:
    def __init__(self, root: str | Path = "data/raw") -> None:
        self.root = Path(root)

    def path_for(self, symbol: str, timeframe: str, source: str = "alpaca") -> Path:
        return self.root / f"source={source}" / f"timeframe={timeframe}" / f"symbol={symbol.upper()}" / "bars.parquet"

    def write_bars(self, df: pd.DataFrame, symbol: str, timeframe: str, source: str = "alpaca") -> Path:
        normalized = normalize_market_data(df, timeframe=timeframe, source=source)
        normalized["symbol"] = symbol.upper()
        normalized["timeframe"] = timeframe
        normalized["source"] = source
        path = self.path_for(symbol, timeframe, source)
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized.to_parquet(path, index=False)
        return path

    def read_bars(
        self,
        symbols: list[str],
        timeframe: str,
        source: str | None = None,
        start: str | None = None,
        end: str | None = None,
        timezone: str = "UTC",
    ) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        sources = [source] if source else [p.name.split("=", 1)[1] for p in self.root.glob("source=*") if p.is_dir()]
        for data_source in sources:
            for symbol in symbols:
                path = self.path_for(symbol, timeframe, data_source)
                if path.exists():
                    frames.append(pd.read_parquet(path))
        if not frames:
            raise FileNotFoundError(f"No local data found for symbols={symbols}, timeframe={timeframe}, source={source}.")
        data = normalize_market_data(
            pd.concat(frames, ignore_index=True),
            timeframe=timeframe,
            source=source or "local",
            timezone=timezone,
        )
        if start:
            data = data[data["timestamp"] >= parse_timestamp_bound(start, timezone)]
        if end:
            data = data[data["timestamp"] <= parse_timestamp_bound(end, timezone)]
        return data.reset_index(drop=True)
