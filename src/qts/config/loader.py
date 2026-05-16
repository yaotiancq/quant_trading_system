from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from qts.config.models import AppConfig


class EnvSettings(BaseSettings):
    alpaca_api_key_id: str | None = None
    alpaca_api_secret_key: str | None = None
    alpaca_paper: bool = True
    alpaca_data_feed: str = "iex"
    qts_config_path: str = "configs/backtest.yaml"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def load_env_settings() -> EnvSettings:
    load_dotenv()
    return EnvSettings()


def load_app_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return AppConfig.model_validate(raw)

