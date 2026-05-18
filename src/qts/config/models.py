from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator


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
    max_portfolio_exposure: float | None = None
    max_symbol_exposure: float = Field(default=1.0, gt=0)
    max_position_notional: float = Field(default=100_000.0, gt=0)
    max_order_notional: float = Field(default=100_000.0, gt=0)
    max_position_quantity: float = Field(default=10_000.0, gt=0)
    max_position_qty: float | None = None
    max_daily_loss: float = Field(default=5_000.0, gt=0)
    allow_short: bool = True
    kill_switch: bool = False
    trading_session_start: str | None = None
    trading_session_end: str | None = None

    @model_validator(mode="after")
    def apply_alias_fields(self) -> "RiskConfig":
        if self.max_portfolio_exposure is not None:
            self.max_gross_exposure = self.max_portfolio_exposure
        if self.max_position_qty is not None:
            self.max_position_quantity = self.max_position_qty
        return self


class BacktestConfig(BaseModel):
    initial_cash: float = Field(default=100_000.0, gt=0)
    commission_per_share: float = Field(default=0.0, ge=0)
    commission_bps: float = Field(default=0.0, ge=0)
    fixed_commission: float = Field(default=0.0, ge=0)
    slippage_bps: float = Field(default=0.0, ge=0)
    latency_bars: int = Field(default=1, ge=1)
    latency_seconds: int = Field(default=0, ge=0)
    annualization_periods: int = Field(default=252, gt=0)
    output_dir: Path = Path("reports/backtests")
    market_order_fill: Literal["next_open", "next_close", "next_vwap", "current_close"] = "next_open"
    market_fill_price: Literal["open", "close", "hlc3", "ohlc4", "vwap"] = "open"
    limit_fill_price: Literal["limit", "touch", "midpoint"] = "limit"
    stop_fill_price: Literal["stop", "market"] = "stop"
    intrabar_price_path: Literal["open_high_low_close", "open_low_high_close"] = "open_high_low_close"
    max_fill_volume_pct: float = Field(default=1.0, gt=0, le=1.0)
    volume_participation_limit: float | None = None
    allow_partial_fills: bool = True

    @field_validator("market_fill_price", mode="before")
    @classmethod
    def normalize_market_fill_price(cls, value: str) -> str:
        aliases = {
            "next_open": "open",
            "next_close": "close",
            "next_vwap": "vwap",
            "current_close": "close",
        }
        return aliases.get(str(value), str(value))

    @model_validator(mode="after")
    def apply_execution_aliases(self) -> "BacktestConfig":
        mapping = {
            "next_open": "open",
            "next_close": "close",
            "next_vwap": "vwap",
            "current_close": "close",
        }
        if "market_order_fill" in self.model_fields_set:
            self.market_fill_price = mapping[self.market_order_fill]
        if self.volume_participation_limit is not None:
            self.max_fill_volume_pct = self.volume_participation_limit
        return self


class ExecutionConfig(BaseModel):
    mode: Literal["backtest", "paper", "live"] = "backtest"
    broker: str = "backtest"
    paper: bool = True
    dry_run: bool = True
    market_order_fill: Literal["next_open", "next_close", "next_vwap", "current_close"] = "next_open"
    slippage_bps: float = Field(default=2.0, ge=0)
    commission_bps: float = Field(default=0.0, ge=0)
    fixed_commission: float = Field(default=0.0, ge=0)
    latency_bars: int = Field(default=1, ge=0)
    latency_seconds: int = Field(default=0, ge=0)
    allow_partial_fills: bool = False
    volume_participation_limit: float = Field(default=0.05, gt=0, le=1.0)
    live_trading_enabled: bool = False
    order_confirmation_required: bool = True
    require_order_confirmation: bool = True
    poll_interval_seconds: int = Field(default=5, gt=0)


class BrokerConfig(BaseModel):
    provider: str = "alpaca"
    paper: bool = True
    live_trading_enabled: bool = False
    require_order_confirmation: bool = True


class AppConfig(BaseModel):
    mode: Literal["backtest", "paper", "live", "research"] = "backtest"
    data: DataConfig
    strategy: StrategyConfig
    risk: RiskConfig = Field(default_factory=RiskConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    broker: BrokerConfig = Field(default_factory=BrokerConfig)
