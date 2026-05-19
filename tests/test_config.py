import pytest
from pydantic import ValidationError

from qts.config.loader import EnvSettings, load_app_config, resolve_app_config
from qts.config.models import AppConfig, BacktestConfig, DataConfig


def test_load_backtest_config() -> None:
    config = load_app_config("configs/config.yaml")
    assert config.mode == "backtest"
    assert config.data.symbols == ["SPY"]
    assert config.data.source == "local"
    assert config.strategy.name == "moving_average_crossover"


def test_unified_config_can_select_ml_profile() -> None:
    config = load_app_config(
        "configs/config.yaml",
        profile_overrides={"strategy": "baseline_ml", "backtest": "ml"},
    )

    assert config.strategy.name == "baseline_ml"
    assert str(config.backtest.output_dir) == "reports/ml_backtests"


def test_unified_config_can_select_paper_profiles() -> None:
    config = load_app_config(
        "configs/config.yaml",
        profile_overrides={
            "mode": "paper",
            "data": "alpaca",
            "risk": "paper",
            "execution": "paper",
            "broker": "alpaca_paper",
        },
    )

    assert config.mode == "paper"
    assert config.data.source == "alpaca"
    assert config.execution.mode == "paper"
    assert config.execution.dry_run
    assert config.broker.paper


def test_direct_config_rejects_profile_overrides_without_profiles() -> None:
    with pytest.raises(ValueError, match="Profile overrides require unified config profiles"):
        resolve_app_config(
            {
                "mode": "backtest",
                "data": {"symbols": ["SPY"]},
                "strategy": {"name": "moving_average_crossover"},
            },
            profile_overrides={"strategy": "baseline_ml"},
        )


def test_config_rejects_mode_execution_mismatch() -> None:
    with pytest.raises(ValidationError, match="must use an execution profile"):
        AppConfig.model_validate(
            {
                "mode": "paper",
                "data": {"symbols": ["SPY"]},
                "strategy": {"name": "moving_average_crossover"},
                "execution": {"mode": "backtest"},
            }
        )


def test_live_mode_requires_explicit_live_enablement() -> None:
    with pytest.raises(ValidationError, match="Live mode requires"):
        AppConfig.model_validate(
            {
                "mode": "live",
                "data": {"symbols": ["SPY"]},
                "strategy": {"name": "moving_average_crossover"},
                "execution": {"mode": "live", "live_trading_enabled": False},
                "broker": {"paper": False, "live_trading_enabled": False},
            }
        )


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


def test_backtest_config_rejects_current_close_fill_by_default() -> None:
    with pytest.raises(ValidationError):
        BacktestConfig(market_order_fill="current_close")


def test_env_settings_accept_required_alpaca_names(monkeypatch) -> None:
    monkeypatch.setenv("ALPACA_API_KEY", "key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "secret")

    settings = EnvSettings()

    assert settings.alpaca_api_key_id == "key"
    assert settings.alpaca_api_secret_key == "secret"
    assert settings.has_alpaca_credentials
