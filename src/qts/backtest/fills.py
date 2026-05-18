from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from qts.backtest.orders import OrderSide, OrderStatus, coerce_order_side


@dataclass(frozen=True)
class FillEvent:
    fill_id: str
    order_id: str
    timestamp: datetime
    symbol: str
    side: OrderSide | str
    quantity: float
    fill_price: float
    commission: float = 0.0
    slippage: float = 0.0
    status: OrderStatus | str = OrderStatus.FILLED
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", self.symbol.upper())
        object.__setattr__(self, "side", coerce_order_side(self.side))
        if not isinstance(self.status, OrderStatus):
            object.__setattr__(self, "status", OrderStatus(str(self.status).lower()))
        if self.quantity <= 0:
            raise ValueError("FillEvent quantity must be positive.")

    @property
    def signed_quantity(self) -> float:
        if self.side in {OrderSide.BUY, OrderSide.BUY_TO_COVER}:
            return self.quantity
        return -self.quantity

    @property
    def filled_quantity(self) -> float:
        return self.quantity

    @property
    def raw_fill_price(self) -> float | None:
        value = self.metadata.get("raw_fill_price")
        return float(value) if value is not None else self.fill_price

    @property
    def remaining_quantity(self) -> float | None:
        value = self.metadata.get("remaining_quantity")
        return float(value) if value is not None else 0.0

    @property
    def requested_quantity(self) -> float:
        value = self.metadata.get("requested_quantity")
        return float(value) if value is not None else self.quantity

    @property
    def fill_status(self) -> str:
        return self.status.value

    @property
    def fill_reason(self) -> object:
        return self.metadata.get("fill_reason")

    @property
    def bar(self) -> object:
        return self.metadata.get("bar")

    @property
    def fill_model(self) -> object:
        return self.metadata.get("fill_model", {})

    @property
    def order(self) -> object:
        return self.metadata.get("order")


__all__ = ["FillEvent"]
