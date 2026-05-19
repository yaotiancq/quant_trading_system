from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml
from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from qts.config.models import AppConfig


class EnvSettings(BaseSettings):
    alpaca_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ALPACA_API_KEY", "ALPACA_API_KEY_ID"),
    )
    alpaca_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ALPACA_SECRET_KEY", "ALPACA_API_SECRET_KEY"),
    )
    alpaca_paper: bool = Field(default=True, validation_alias="ALPACA_PAPER")
    alpaca_data_feed: str = Field(default="iex", validation_alias="ALPACA_DATA_FEED")
    qts_config_path: str = Field(default="configs/config.yaml", validation_alias="QTS_CONFIG_PATH")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def alpaca_api_key_id(self) -> str | None:
        return self.alpaca_api_key

    @property
    def alpaca_api_secret_key(self) -> str | None:
        return self.alpaca_secret_key

    @property
    def has_alpaca_credentials(self) -> bool:
        return bool(self.alpaca_api_key and self.alpaca_secret_key)


def load_env_settings() -> EnvSettings:
    load_dotenv()
    return EnvSettings()


def load_app_config(path: str | Path, profile_overrides: Mapping[str, str | None] | None = None) -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    resolved = resolve_app_config(raw, profile_overrides=profile_overrides)
    return AppConfig.model_validate(resolved)


def resolve_app_config(
    raw: Mapping[str, Any],
    profile_overrides: Mapping[str, str | None] | None = None,
) -> dict[str, Any]:
    """Resolve either direct AppConfig YAML or unified profile-based YAML.

    The single-file config format keeps named profiles under ``profiles`` and
    chooses active profiles from ``runtime``. This function flattens that into
    the direct AppConfig shape used by the application core. Existing direct
    config files remain valid for users with local custom configs.
    """

    overrides = {key: value for key, value in (profile_overrides or {}).items() if value}
    if "profiles" not in raw:
        unsupported = sorted(key for key in overrides if key != "mode")
        if unsupported:
            names = ", ".join(unsupported)
            raise ValueError(f"Profile overrides require unified config profiles. Unsupported overrides: {names}.")
        resolved = dict(raw)
        if "mode" in overrides:
            resolved["mode"] = overrides["mode"]
        return resolved

    runtime = dict(raw.get("runtime") or {})
    profiles = raw.get("profiles") or {}
    if not isinstance(profiles, Mapping):
        raise ValueError("Unified config must define profiles as a mapping.")

    mode = str(overrides.get("mode") or runtime.get("mode") or "backtest")
    data_name = str(overrides.get("data") or runtime.get("data") or "sample_local")
    strategy_name = str(overrides.get("strategy") or runtime.get("strategy") or "moving_average_crossover")
    risk_name = str(overrides.get("risk") or runtime.get("risk") or "research")
    backtest_name = str(overrides.get("backtest") or runtime.get("backtest") or "default")
    execution_name = str(overrides.get("execution") or runtime.get("execution") or mode)
    broker_name = str(overrides.get("broker") or runtime.get("broker") or "alpaca_paper")

    strategy = _profile(profiles, "strategies", strategy_name)
    strategy.setdefault("name", strategy_name)

    resolved = {
        "mode": mode,
        "data": _profile(profiles, "data", data_name),
        "strategy": strategy,
        "risk": _profile(profiles, "risk", risk_name),
        "backtest": _profile(profiles, "backtest", backtest_name),
        "execution": _profile(profiles, "execution", execution_name),
        "broker": _profile(profiles, "broker", broker_name),
    }
    return resolved


def _profile(profiles: Mapping[str, Any], group: str, name: str) -> dict[str, Any]:
    group_profiles = profiles.get(group)
    if not isinstance(group_profiles, Mapping):
        raise ValueError(f"Unified config is missing profiles.{group}.")
    selected = group_profiles.get(name)
    if selected is None:
        available = ", ".join(sorted(str(key) for key in group_profiles)) or "none"
        raise ValueError(f"Unknown {group} profile '{name}'. Available profiles: {available}.")
    if not isinstance(selected, Mapping):
        raise ValueError(f"profiles.{group}.{name} must be a mapping.")
    return dict(selected)
