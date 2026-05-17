import pytest
from pydantic import ValidationError

from qts.config.loader import EnvSettings, load_app_config
from qts.config.models import BacktestConfig, DataConfig


def test_load_backtest_config() -> None:
    config = load_app_config("configs/backtest.yaml")
    assert config.mode == "backtest"
    assert config.data.symbols == ["SPY"]
    assert config.strategy.name == "moving_average_crossover"


def test_symbols_are_normalized() -> None:
    config = DataConfig(symbols=[" spy ", "aapl"])
    assert config.symbols == ["SPY", "AAPL"]


def test_timezone_defaults_to_pacific_time() -> None:
    config = DataConfig()
    assert config.timezone == "America/Los_Angeles"


def test_timezone_accepts_pt_alias() -> None:
    config = DataConfig(timezone="PT")
    assert config.timezone == "America/Los_Angeles"


def test_backtest_config_rejects_zero_latency() -> None:
    with pytest.raises(ValidationError):
        BacktestConfig(latency_bars=0)


def test_env_settings_accept_required_alpaca_names(monkeypatch) -> None:
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")

    settings = EnvSettings()

    assert settings.alpaca_api_key_id == "key"
    assert settings.alpaca_api_secret_key == "secret"
    assert settings.has_alpaca_credentials
