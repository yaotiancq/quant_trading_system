from __future__ import annotations

from pathlib import Path

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
    qts_config_path: str = Field(default="configs/backtest.yaml", validation_alias="QTS_CONFIG_PATH")

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


def load_app_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return AppConfig.model_validate(raw)
