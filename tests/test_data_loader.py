from pathlib import Path

from qts.config.models import DataConfig
from qts.data.loader import load_market_data
from qts.data.storage import ParquetDataStore


def test_load_sample_market_data() -> None:
    data = load_market_data(DataConfig(data_file=Path("data/raw/sample_bars.csv"), source="local", symbols=["SPY"]))
    assert not data.empty
    assert set(["timestamp", "symbol", "open", "high", "low", "close", "volume"]).issubset(data.columns)
    assert data["symbol"].unique().tolist() == ["SPY"]
    assert str(data["timestamp"].dt.tz) == "America/Los_Angeles"
    assert data["timestamp"].iloc[0].hour == 6


def test_parquet_data_store_round_trip(tmp_path) -> None:
    data = load_market_data(DataConfig(data_file=Path("data/raw/sample_bars.csv"), source="local", symbols=["SPY"])).head(5)
    store = ParquetDataStore(tmp_path)
    path = store.write_bars(data, symbol="SPY", timeframe="1Min", source="unit")

    loaded = store.read_bars(["SPY"], timeframe="1Min", source="unit", timezone="America/Los_Angeles")

    assert path.exists()
    assert len(loaded) == 5
    assert loaded["source"].unique().tolist() == ["unit"]
    assert str(loaded["timestamp"].dt.tz) == "America/Los_Angeles"


def test_load_market_data_from_configured_csv(tmp_path) -> None:
    source = Path("data/raw/sample_bars.csv")
    data_file = tmp_path / "custom.csv"
    data_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    data = load_market_data(
        DataConfig(
            data_file=data_file,
            source="custom",
            timeframe="1Min",
            timezone="America/Los_Angeles",
            symbols=["spy"],
            start="2024-01-02T14:30:00Z",
            end="2024-01-02T14:31:00Z",
        )
    )

    assert len(data) == 2
    assert data["symbol"].unique().tolist() == ["SPY"]
    assert data["source"].unique().tolist() == ["custom"]
    assert data["timestamp"].iloc[0].hour == 6
