from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class DataConfig(BaseModel):
    data_dir: Path = Path("data/raw")
    data_file: Path | None = None
    source: str = "local"
    timeframe: str = "1Min"
    timezone: str = "America/Los_Angeles"
    symbols: list[str] = Field(default_factory=list)
    start: str | None = None
    end: str | None = None
    feed: str = "iex"

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, value: list[str]) -> list[str]:
        return [symbol.strip().upper() for symbol in value if symbol.strip()]

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        aliases = {
            "PT": "America/Los_Angeles",
            "PST": "America/Los_Angeles",
            "PDT": "America/Los_Angeles",
            "US/PACIFIC": "America/Los_Angeles",
        }
        normalized = aliases.get(value.strip().upper(), value.strip())
        try:
            ZoneInfo(normalized)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {value}") from exc
        return normalized


class StrategyConfig(BaseModel):
    name: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class RiskConfig(BaseModel):
    max_gross_exposure: float = Field(default=1.0, gt=0)
    max_symbol_exposure: float = Field(default=1.0, gt=0)
    max_position_notional: float = Field(default=100_000.0, gt=0)
    max_order_notional: float = Field(default=100_000.0, gt=0)
    max_position_quantity: float = Field(default=10_000.0, gt=0)
    max_daily_loss: float = Field(default=5_000.0, gt=0)
    allow_short: bool = True
    kill_switch: bool = False
    trading_session_start: str | None = None
    trading_session_end: str | None = None


class BacktestConfig(BaseModel):
    initial_cash: float = Field(default=100_000.0, gt=0)
    commission_per_share: float = Field(default=0.0, ge=0)
    slippage_bps: float = Field(default=0.0, ge=0)
    latency_bars: int = Field(default=1, ge=1)
    annualization_periods: int = Field(default=252, gt=0)
    output_dir: Path = Path("reports/backtests")


class ExecutionConfig(BaseModel):
    broker: str = "alpaca"
    paper: bool = True
    dry_run: bool = True
    live_trading_enabled: bool = False
    order_confirmation_required: bool = True
    poll_interval_seconds: int = Field(default=5, gt=0)


class AppConfig(BaseModel):
    mode: Literal["backtest", "paper", "live", "research"] = "backtest"
    data: DataConfig
    strategy: StrategyConfig
    risk: RiskConfig = Field(default_factory=RiskConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
