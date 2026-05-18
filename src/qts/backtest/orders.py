from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"
    SELL_SHORT = "sell_short"
    BUY_TO_COVER = "buy_to_cover"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderStatus(str, Enum):
    NEW = "new"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    CANCELLED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True)
class OrderRequest:
    timestamp: datetime
    symbol: str
    side: OrderSide | str
    quantity: float | None = None
    notional: float | None = None
    order_type: OrderType | str = OrderType.MARKET
    limit_price: float | None = None
    stop_price: float | None = None
    time_in_force: Literal["day", "gtc", "opg", "cls", "ioc", "fok"] | str = "day"
    order_id: str | None = None
    strategy_id: str | None = None
    trail_price: float | None = None
    trail_percent: float | None = None
    extended_hours: bool = False
    order_class: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", self.symbol.upper())
        object.__setattr__(self, "side", coerce_order_side(self.side))
        object.__setattr__(self, "order_type", coerce_order_type(self.order_type))
        object.__setattr__(self, "time_in_force", str(self.time_in_force).lower())
        if self.quantity is None and self.notional is None:
            raise ValueError("OrderRequest requires quantity or notional.")
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("OrderRequest quantity must be positive.")
        if self.notional is not None and self.notional <= 0:
            raise ValueError("OrderRequest notional must be positive.")


def coerce_order_side(value: OrderSide | str) -> OrderSide:
    if isinstance(value, OrderSide):
        return value
    normalized = str(value).lower()
    aliases = {
        "buy": OrderSide.BUY,
        "sell": OrderSide.SELL,
        "sell_short": OrderSide.SELL_SHORT,
        "short": OrderSide.SELL_SHORT,
        "buy_to_cover": OrderSide.BUY_TO_COVER,
        "cover": OrderSide.BUY_TO_COVER,
    }
    if normalized not in aliases:
        raise ValueError(f"Unsupported order side: {value}")
    return aliases[normalized]


def coerce_order_type(value: OrderType | str) -> OrderType:
    if isinstance(value, OrderType):
        return value
    normalized = str(value).lower()
    aliases = {
        "market": OrderType.MARKET,
        "limit": OrderType.LIMIT,
        "stop": OrderType.STOP,
        "stop_limit": OrderType.STOP_LIMIT,
        "trailing_stop": OrderType.TRAILING_STOP,
    }
    if normalized not in aliases:
        raise ValueError(f"Unsupported order type: {value}")
    return aliases[normalized]


__all__ = ["OrderRequest", "OrderSide", "OrderStatus", "OrderType", "coerce_order_side", "coerce_order_type"]
