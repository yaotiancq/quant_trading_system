from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from qts.data.storage import ParquetDataStore
from qts.data.validation import normalize_market_data
from qts.utils.logging import configure_logging, get_logger


def generate_sample_bars(
    symbols: list[str],
    start_date: str,
    days: int,
    timeframe: str = "1Min",
    seed: int = 42,
) -> pd.DataFrame:
    if timeframe not in {"1Min", "1Sec"}:
        raise ValueError("Sample generator supports 1Min and 1Sec bars.")
    if days < 1:
        raise ValueError("days must be at least 1.")

    rng = np.random.default_rng(seed)
    freq = "min" if timeframe == "1Min" else "s"
    periods_per_day = 390 if timeframe == "1Min" else 60 * 60
    start = pd.Timestamp(start_date)
    if start.tzinfo is None:
        start = start.tz_localize("America/New_York")
    start = start.tz_convert("America/New_York")

    frames: list[pd.DataFrame] = []
    base_prices = {"SPY": 470.0, "AAPL": 185.0, "MSFT": 375.0}
    for symbol_index, symbol in enumerate(symbol.upper() for symbol in symbols):
        rows: list[dict[str, object]] = []
        price = base_prices.get(symbol, 100.0 + symbol_index * 25.0)
        for day_index in range(days):
            session_start = (start.normalize() + pd.Timedelta(days=day_index)).replace(hour=9, minute=30, second=0)
            timestamps = pd.date_range(session_start, periods=periods_per_day, freq=freq, tz="America/New_York")
            trend = np.sin(np.linspace(0, 4 * np.pi, periods_per_day)) * 0.0008
            drift = 0.00005 * (1 if day_index % 2 == 0 else -1)
            noise = rng.normal(0.0, 0.0007, periods_per_day)
            returns = drift + trend + noise
            for timestamp, ret in zip(timestamps, returns):
                open_price = price
                close_price = max(1.0, open_price * (1.0 + ret))
                spread = abs(close_price - open_price) + max(0.01, open_price * 0.0005)
                high = max(open_price, close_price) + spread * 0.35
                low = min(open_price, close_price) - spread * 0.35
                volume = int(rng.integers(20_000, 120_000) * (1.0 + 0.2 * np.sin(timestamp.minute / 60 * 2 * np.pi)))
                trade_count = max(1, int(volume / rng.integers(150, 450)))
                vwap = (open_price + high + low + close_price) / 4.0
                rows.append(
                    {
                        "timestamp": timestamp.tz_convert("UTC").isoformat(),
                        "symbol": symbol,
                        "open": round(open_price, 4),
                        "high": round(high, 4),
                        "low": round(low, 4),
                        "close": round(close_price, 4),
                        "volume": float(volume),
                        "trade_count": float(trade_count),
                        "vwap": round(vwap, 4),
                        "timeframe": timeframe,
                        "source": "local",
                    }
                )
                price = close_price
        frames.append(pd.DataFrame(rows))

    return normalize_market_data(pd.concat(frames, ignore_index=True), timeframe=timeframe, source="local", timezone="UTC")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic local OHLCV sample data.")
    parser.add_argument("--output", default="data/raw/sample_bars.csv")
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--symbols", nargs="+", default=["SPY"])
    parser.add_argument("--start-date", default="2024-01-02")
    parser.add_argument("--days", type=int, default=5)
    parser.add_argument("--timeframe", choices=["1Min", "1Sec"], default="1Min")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-parquet", action="store_true", help="Skip writing partitioned Parquet files.")
    args = parser.parse_args()

    configure_logging()
    logger = get_logger(__name__)
    bars = generate_sample_bars(args.symbols, args.start_date, args.days, timeframe=args.timeframe, seed=args.seed)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(output, index=False)
    logger.info("Wrote %s rows to %s", len(bars), output)

    if not args.no_parquet:
        store = ParquetDataStore(args.data_dir)
        for symbol in sorted(bars["symbol"].unique()):
            path = store.write_bars(bars[bars["symbol"] == symbol], symbol=symbol, timeframe=args.timeframe, source="local")
            logger.info("Wrote %s", path)


if __name__ == "__main__":
    main()
