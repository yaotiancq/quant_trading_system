from pathlib import Path
import argparse

import pandas as pd


def inspect_parquet(file_path: Path) -> None:
    if not file_path.exists():
        raise FileNotFoundError(f"Cannot find file: {file_path}")

    df = pd.read_parquet(file_path)

    print("=" * 80)
    print("File:")
    print(file_path.resolve())

    print("=" * 80)
    print("Shape:")
    print(df.shape)

    print("=" * 80)
    print("Columns:")
    print(df.columns.tolist())

    print("=" * 80)
    print("Data types:")
    print(df.dtypes)

    print("=" * 80)
    print("First 10 rows:")
    print(df.head(10))

    print("=" * 80)
    print("Last 10 rows:")
    print(df.tail(10))

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        print("=" * 80)
        print("Timestamp range:")
        print("Start:", df["timestamp"].min())
        print("End:  ", df["timestamp"].max())

    if "symbol" in df.columns:
        print("=" * 80)
        print("Symbols:")
        symbols = sorted(df["symbol"].dropna().unique().tolist())
        print(symbols)

        print("=" * 80)
        print("Rows per symbol:")
        print(df["symbol"].value_counts())

    if {"symbol", "timestamp"}.issubset(df.columns):
        print("=" * 80)
        print("Latest row per symbol:")
        latest = (
            df.sort_values("timestamp")
            .groupby("symbol", as_index=False)
            .tail(1)
            .sort_values("symbol")
        )
        print(latest)

    price_cols = ["open", "high", "low", "close", "volume"]
    existing_price_cols = [col for col in price_cols if col in df.columns]

    if existing_price_cols:
        print("=" * 80)
        print("Basic price/volume summary:")
        print(df[existing_price_cols].describe())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect a parquet market data file."
    )

    parser.add_argument(
        "file_path",
        help="Path to the parquet file, for example: data/raw/bars.parquet",
    )

    args = parser.parse_args()

    file_path = Path(args.file_path)
    inspect_parquet(file_path)


if __name__ == "__main__":
    main()