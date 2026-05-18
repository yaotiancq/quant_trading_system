from __future__ import annotations

from dataclasses import dataclass, field

from qts.backtest.fills import FillEvent


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


@dataclass(frozen=True)
class AccountSnapshot:
    cash: float
    equity: float
    buying_power: float
    realized_pnl: float
    unrealized_pnl: float


@dataclass(frozen=True)
class PositionSnapshot:
    symbol: str
    qty: float
    average_price: float
    market_value: float
    unrealized_pnl: float


@dataclass
class Portfolio:
    initial_cash: float
    cash: float = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    fill_history: list[FillEvent] = field(default_factory=list)
    trade_history: list[FillResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cash = self.initial_cash

    def market_value(self, prices: dict[str, float]) -> float:
        return sum(pos.quantity * prices.get(symbol, pos.average_price) for symbol, pos in self.positions.items())

    def equity(self, prices: dict[str, float]) -> float:
        return self.cash + self.market_value(prices)

    def unrealized_pnl(self, prices: dict[str, float]) -> float:
        return sum(
            (prices.get(symbol, pos.average_price) - pos.average_price) * pos.quantity
            for symbol, pos in self.positions.items()
        )

    def buying_power(self, prices: dict[str, float]) -> float:
        return max(self.cash, 0.0) + max(self.equity(prices), 0.0)

    def account_snapshot(self, prices: dict[str, float]) -> AccountSnapshot:
        return AccountSnapshot(
            cash=self.cash,
            equity=self.equity(prices),
            buying_power=self.buying_power(prices),
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl(prices),
        )

    def position_snapshots(self, prices: dict[str, float]) -> list[PositionSnapshot]:
        snapshots: list[PositionSnapshot] = []
        for symbol, position in self.positions.items():
            price = prices.get(symbol, position.average_price)
            snapshots.append(
                PositionSnapshot(
                    symbol=symbol,
                    qty=position.quantity,
                    average_price=position.average_price,
                    market_value=position.quantity * price,
                    unrealized_pnl=(price - position.average_price) * position.quantity,
                )
            )
        return snapshots

    def apply_fill_event(self, fill_event: FillEvent) -> FillResult:
        result = self._apply_fill_values(
            fill_event.symbol,
            fill_event.signed_quantity,
            fill_event.fill_price,
            fill_event.commission,
        )
        self.fill_history.append(fill_event)
        self.trade_history.append(result)
        if result.realized_pnl is not None:
            self.realized_pnl += result.realized_pnl
        return result

    def _apply_fill_values(self, symbol: str, signed_quantity: float, fill_price: float, commission: float) -> FillResult:
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
