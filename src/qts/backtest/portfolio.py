from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from qts.execution.order_planner import plan_orders_from_targets
from qts.strategies.base import OrderRequest, TargetPosition


@dataclass
class Position:
    quantity: float = 0.0
    average_price: float = 0.0


@dataclass(frozen=True)
class FillResult:
    symbol: str
    signed_quantity: float
    fill_price: float
    commission: float
    before_quantity: float
    before_average_price: float
    after_quantity: float
    after_average_price: float
    closed_quantity: float
    realized_pnl: float | None


@dataclass
class Portfolio:
    initial_cash: float
    cash: float = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.cash = self.initial_cash

    def market_value(self, prices: dict[str, float]) -> float:
        return sum(pos.quantity * prices.get(symbol, pos.average_price) for symbol, pos in self.positions.items())

    def equity(self, prices: dict[str, float]) -> float:
        return self.cash + self.market_value(prices)

    def orders_for_targets(
        self,
        targets: list[TargetPosition],
        prices: dict[str, float],
        timestamp: pd.Timestamp,
        max_position_notional: float,
    ) -> list[OrderRequest]:
        current_quantities = {symbol: position.quantity for symbol, position in self.positions.items()}
        return plan_orders_from_targets(
            targets=targets,
            equity=self.equity(prices),
            current_quantities=current_quantities,
            latest_prices=prices,
            timestamp=timestamp,
            max_position_notional=max_position_notional,
        )

    def apply_fill(self, symbol: str, signed_quantity: float, fill_price: float, commission: float) -> FillResult:
        position = self.positions.setdefault(symbol, Position())
        before_qty = position.quantity
        before_avg = position.average_price
        self.cash -= signed_quantity * fill_price + commission
        new_qty = before_qty + signed_quantity
        closed_qty = 0.0
        realized_pnl = None

        if before_qty and (before_qty > 0) != (signed_quantity > 0):
            closed_qty = min(abs(before_qty), abs(signed_quantity))
            realized_pnl = (fill_price - before_avg) * closed_qty * (1 if before_qty > 0 else -1) - commission

        if abs(new_qty) < 1e-9:
            position.quantity = 0.0
            position.average_price = 0.0
        elif before_qty == 0 or (before_qty > 0) == (signed_quantity > 0):
            total_cost = before_avg * before_qty + fill_price * signed_quantity
            position.average_price = total_cost / new_qty
            position.quantity = new_qty
        elif abs(signed_quantity) > abs(before_qty):
            position.quantity = new_qty
            position.average_price = fill_price
        else:
            position.quantity = new_qty
            position.average_price = before_avg

        return FillResult(
            symbol=symbol,
            signed_quantity=signed_quantity,
            fill_price=fill_price,
            commission=commission,
            before_quantity=before_qty,
            before_average_price=before_avg,
            after_quantity=position.quantity,
            after_average_price=position.average_price,
            closed_quantity=closed_qty,
            realized_pnl=realized_pnl,
        )
