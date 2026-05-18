from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

import pandas as pd

from qts.backtest.execution import BarExecutionSimulator, SimulatedFill
from qts.backtest.fills import FillEvent
from qts.backtest.orders import OrderRequest, OrderSide, OrderStatus
from qts.backtest.portfolio import FillResult, Portfolio
from qts.config.models import BacktestConfig


@dataclass
class BacktestOrder:
    order_id: str
    request: OrderRequest
    submitted_at: pd.Timestamp
    submitted_index: int
    ready_index: int
    ready_at: pd.Timestamp | None = None
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    average_fill_price: float | None = None
    last_status_at: pd.Timestamp | None = None
    trail_hwm: float | None = None
    attempts: int = 0
    status_reason: str = "new"
    history: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.remaining_quantity = float(self.request.quantity or 0.0)
        self.last_status_at = self.submitted_at
        self.history.append(self._event_row(self.submitted_at, self.status, self.status_reason))

    @property
    def is_open(self) -> bool:
        return self.status in {OrderStatus.NEW, OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}

    def transition(self, timestamp: pd.Timestamp, status: OrderStatus, reason: str) -> None:
        self.status = status
        self.status_reason = reason
        self.last_status_at = timestamp
        self.history.append(self._event_row(timestamp, status, reason))

    def add_fill(self, timestamp: pd.Timestamp, quantity: float, price: float, status: OrderStatus, reason: str) -> None:
        previous_notional = (self.average_fill_price or 0.0) * self.filled_quantity
        new_notional = previous_notional + quantity * price
        self.filled_quantity += quantity
        self.remaining_quantity = max(self.remaining_quantity - quantity, 0.0)
        self.average_fill_price = new_notional / self.filled_quantity if self.filled_quantity else None
        self.transition(timestamp, status, reason)

    def _event_row(self, timestamp: pd.Timestamp, status: OrderStatus, reason: str) -> dict[str, object]:
        return {
            "order_id": self.order_id,
            "timestamp": timestamp,
            "status": status.value,
            "reason": reason,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
        }


class BacktestBroker:
    """Backtest implementation of the shared BrokerAdapter interface."""

    def __init__(
        self,
        config: BacktestConfig,
        execution: BarExecutionSimulator | None = None,
        portfolio: Portfolio | None = None,
    ) -> None:
        self.config = config
        self.execution = execution or BarExecutionSimulator(config)
        self.portfolio = portfolio or Portfolio(config.initial_cash)
        self.orders: dict[str, BacktestOrder] = {}
        self.latest_prices: dict[str, float] = {}
        self.max_position_notional = float("inf")
        self.current_timestamp: pd.Timestamp | None = None
        self.current_bar_index = 0
        self._sequence = 0
        self._fill_sequence = 0
        self._entry_state: dict[str, tuple[float, int]] = {}
        self._trade_rows: list[dict[str, object]] = []

    def set_clock(self, timestamp: pd.Timestamp | datetime, bar_index: int) -> None:
        self.current_timestamp = pd.Timestamp(timestamp)
        self.current_bar_index = bar_index

    def submit_order(self, order: OrderRequest) -> BacktestOrder:
        if self.current_timestamp is None:
            raise RuntimeError("BacktestBroker clock must be set before submitting orders.")
        order = self._with_quantity_and_order_id(order)
        self._sequence += 1
        order_id = order.order_id or f"BT-{self._sequence:08d}"
        order = replace(order, order_id=order_id)
        record = BacktestOrder(
            order_id=order_id,
            request=order,
            submitted_at=self.current_timestamp,
            submitted_index=self.current_bar_index,
            ready_index=self.current_bar_index + max(self.config.latency_bars, 0),
            ready_at=self._ready_at(),
            status=OrderStatus.ACCEPTED,
            status_reason="accepted",
        )
        record.history[-1]["status"] = OrderStatus.ACCEPTED.value
        record.history[-1]["reason"] = "accepted"
        self.orders[order_id] = record
        return record

    def cancel_order(self, order_id: str) -> None:
        record = self.orders[order_id]
        if record.is_open:
            record.transition(self._now(), OrderStatus.CANCELED, "canceled")

    def get_order_status(self, order_id: str) -> OrderStatus:
        return self.orders[order_id].status

    def get_open_orders(self) -> list[BacktestOrder]:
        return [record for record in self.orders.values() if record.is_open]

    def get_positions(self) -> list[object]:
        return self.portfolio.position_snapshots(self.latest_prices)

    def get_account(self) -> object:
        return self.portfolio.account_snapshot(self.latest_prices)

    def get_cash(self) -> float:
        return self.portfolio.cash

    def get_clock(self) -> object:
        return {"timestamp": self.current_timestamp, "bar_index": self.current_bar_index}

    def get_equity(self) -> float:
        return self.portfolio.equity(self.latest_prices)

    def get_market_value(self) -> float:
        return self.portfolio.market_value(self.latest_prices)

    def gross_exposure(self) -> float:
        equity = self.get_equity()
        if not equity:
            return 0.0
        gross = sum(
            abs(position.qty * self.latest_prices.get(position.symbol, position.average_price))
            for position in self.get_positions()
        )
        return gross / equity

    def flatten_orders(self, timestamp: pd.Timestamp) -> list[OrderRequest]:
        orders: list[OrderRequest] = []
        for position in self.get_positions():
            if abs(position.qty) <= 1e-9:
                continue
            orders.append(
                OrderRequest(
                    timestamp=pd.Timestamp(timestamp).to_pydatetime(),
                    symbol=position.symbol,
                    side=OrderSide.SELL if position.qty > 0 else OrderSide.BUY_TO_COVER,
                    quantity=abs(position.qty),
                    metadata={"reason": "risk_flatten"},
                )
            )
        return orders

    def open_order_quantities(self) -> dict[str, float]:
        quantities: dict[str, float] = {}
        for record in self.get_open_orders():
            signed = record.remaining_quantity if record.request.side in {OrderSide.BUY, OrderSide.BUY_TO_COVER} else -record.remaining_quantity
            quantities[record.request.symbol] = quantities.get(record.request.symbol, 0.0) + signed
        return quantities

    def open_order_count(self) -> int:
        return len(self.get_open_orders())

    def process_bar(self, timestamp: pd.Timestamp, bar_index: int, bars: pd.DataFrame) -> list[FillEvent]:
        self.set_clock(timestamp, bar_index)
        self.latest_prices.update({str(row["symbol"]).upper(): float(row["close"]) for _, row in bars.iterrows()})
        current_by_symbol = {str(row["symbol"]).upper(): row for _, row in bars.iterrows()}
        fills: list[FillEvent] = []
        for record in list(self.orders.values()):
            if not record.is_open or record.ready_index > bar_index or self._before_ready_time(record):
                continue
            if self.execution.is_expired(record.request, self._now()):
                record.transition(self._now(), OrderStatus.EXPIRED, "day_order_expired")
                continue

            bar = current_by_symbol.get(record.request.symbol)
            if bar is None:
                record.attempts += 1
                continue

            simulated = self.execution.simulate(record.request, bar, trail_hwm=record.trail_hwm)
            record.trail_hwm = simulated.trail_hwm
            record.attempts += 1
            if not simulated.has_fill:
                self._handle_unfilled(record, simulated)
                continue

            fill_event = self._build_fill_event(record, simulated, bar)
            status = OrderStatus.FILLED if simulated.remaining_quantity <= 1e-9 else OrderStatus.PARTIALLY_FILLED
            record.add_fill(self._now(), fill_event.quantity, fill_event.fill_price, status, simulated.reason)
            fill_result = self.portfolio.apply_fill_event(fill_event)
            self._record_trade(fill_event, fill_result, bar)
            fills.append(fill_event)

            if record.remaining_quantity > 1e-9 and record.request.time_in_force not in {"ioc", "fok", "opg", "cls"}:
                record.request = replace(record.request, quantity=record.remaining_quantity)
                record.ready_index = bar_index + 1
            elif record.remaining_quantity > 1e-9:
                record.remaining_quantity = 0.0
                record.transition(self._now(), OrderStatus.CANCELED, "unfilled_remainder_canceled")
        return fills

    def order_log(self) -> pd.DataFrame:
        rows = [
            {
                "order_id": record.order_id,
                "symbol": record.request.symbol,
                "side": record.request.side.value,
                "order_type": record.request.order_type.value,
                "time_in_force": record.request.time_in_force,
                "submitted_at": record.submitted_at,
                "submitted_index": record.submitted_index,
                "ready_index": record.ready_index,
                "ready_at": record.ready_at,
                "status": record.status.value,
                "status_reason": record.status_reason,
                "quantity": record.filled_quantity + record.remaining_quantity,
                "current_order_quantity": record.request.quantity,
                "notional": record.request.notional,
                "filled_quantity": record.filled_quantity,
                "remaining_quantity": record.remaining_quantity,
                "average_fill_price": record.average_fill_price,
                "limit_price": record.request.limit_price,
                "stop_price": record.request.stop_price,
                "strategy_id": record.request.strategy_id,
                "extended_hours": record.request.extended_hours,
                "order_class": record.request.order_class,
                "last_status_at": record.last_status_at,
                "attempts": record.attempts,
            }
            for record in self.orders.values()
        ]
        return pd.DataFrame(rows)

    def order_events(self) -> pd.DataFrame:
        rows = [event for record in self.orders.values() for event in record.history]
        return pd.DataFrame(rows)

    def trade_log(self) -> pd.DataFrame:
        return pd.DataFrame(self._trade_rows)

    def fill_model_snapshot(self) -> dict[str, object]:
        return {
            "market_order_fill": self.config.market_order_fill,
            "market_fill_price": self.config.market_fill_price,
            "limit_fill_price": self.config.limit_fill_price,
            "stop_fill_price": self.config.stop_fill_price,
            "intrabar_price_path": self.config.intrabar_price_path,
            "max_fill_volume_pct": self.config.max_fill_volume_pct,
            "allow_partial_fills": self.config.allow_partial_fills,
            "slippage_bps": self.config.slippage_bps,
            "commission_bps": self.config.commission_bps,
            "fixed_commission": self.config.fixed_commission,
            "latency_bars": self.config.latency_bars,
        }

    def _with_quantity_and_order_id(self, order: OrderRequest) -> OrderRequest:
        if order.quantity is not None:
            return order
        if order.notional is None:
            return order
        price = self.latest_prices.get(order.symbol)
        if price is None or price <= 0:
            raise ValueError(f"Cannot infer quantity for notional order without a latest price: {order.symbol}")
        return replace(order, quantity=order.notional / price)

    def _build_fill_event(self, record: BacktestOrder, simulated: SimulatedFill, bar: pd.Series) -> FillEvent:
        signed_quantity = simulated.filled_quantity if record.request.side in {OrderSide.BUY, OrderSide.BUY_TO_COVER} else -simulated.filled_quantity
        fill_price = self.execution.apply_slippage(simulated.fill_price, signed_quantity)
        commission = self.execution.commission(simulated.filled_quantity, fill_price)
        self._fill_sequence += 1
        raw_fill_price = float(simulated.fill_price)
        return FillEvent(
            fill_id=f"FILL-{self._fill_sequence:08d}",
            order_id=record.order_id,
            timestamp=self._now().to_pydatetime(),
            symbol=record.request.symbol,
            side=record.request.side,
            quantity=simulated.filled_quantity,
            fill_price=fill_price,
            commission=commission,
            slippage=fill_price - raw_fill_price,
            status=OrderStatus.FILLED if simulated.remaining_quantity <= 1e-9 else OrderStatus.PARTIALLY_FILLED,
            metadata={
                "order": record.request,
                "requested_quantity": record.request.quantity,
                "remaining_quantity": max(record.remaining_quantity - simulated.filled_quantity, 0.0),
                "raw_fill_price": raw_fill_price,
                "fill_reason": simulated.reason,
                "bar": bar,
                "fill_model": self.fill_model_snapshot(),
            },
        )

    def _record_trade(self, fill_event: FillEvent, fill_result: FillResult, bar: pd.Series) -> None:
        order = fill_event.metadata["order"]
        opened_index = self._entry_state.get(order.symbol, (0.0, self.current_bar_index))[1]
        trade_return = None
        holding_period_bars = None
        if fill_result.realized_pnl is not None:
            holding_period_bars = self.current_bar_index - opened_index
            trade_return = fill_result.realized_pnl / (abs(fill_result.before_average_price * fill_result.closed_quantity) or 1.0)
        if fill_result.after_quantity and (
            not fill_result.before_quantity or (fill_result.before_quantity > 0) != (fill_result.after_quantity > 0)
        ):
            self._entry_state[order.symbol] = (fill_event.fill_price, self.current_bar_index)
        elif not fill_result.after_quantity:
            self._entry_state.pop(order.symbol, None)
        self._trade_rows.append(
            {
                "timestamp": fill_event.timestamp,
                "fill_id": fill_event.fill_id,
                "order_id": fill_event.order_id,
                "symbol": fill_event.symbol,
                "side": fill_event.side.value,
                "quantity": fill_event.quantity,
                "requested_quantity": fill_event.metadata.get("requested_quantity"),
                "remaining_quantity": fill_event.metadata.get("remaining_quantity"),
                "order_type": order.order_type.value,
                "time_in_force": order.time_in_force,
                "limit_price": order.limit_price,
                "stop_price": order.stop_price,
                "raw_fill_price": fill_event.metadata.get("raw_fill_price"),
                "fill_price": fill_event.fill_price,
                "slippage": fill_event.slippage,
                "fill_status": fill_event.status.value,
                "fill_reason": fill_event.metadata.get("fill_reason"),
                "fill_bar_open": float(bar["open"]),
                "fill_bar_high": float(bar["high"]),
                "fill_bar_low": float(bar["low"]),
                "fill_bar_close": float(bar["close"]),
                "fill_bar_vwap": float(bar["vwap"]) if pd.notna(bar.get("vwap")) else None,
                "fill_bar_volume": float(bar["volume"]),
                "fill_model": fill_event.metadata.get("fill_model"),
                "commission": fill_event.commission,
                "cash_after": self.portfolio.cash,
                "position_after": fill_result.after_quantity,
                "average_price_after": fill_result.after_average_price,
                "closed_quantity": fill_result.closed_quantity,
                "realized_pnl": fill_result.realized_pnl,
                "trade_return": trade_return,
                "holding_period_bars": holding_period_bars,
                "signal_source_name": order.metadata.get("signal_source_name"),
                "signal_source_type": order.metadata.get("signal_source_type"),
                "signal_model_version": order.metadata.get("signal_model_version"),
                "signal_feature_set": order.metadata.get("signal_feature_set"),
                "signal_confidence": order.metadata.get("signal_confidence"),
                "signal_confidence_metadata": order.metadata.get("signal_confidence_metadata"),
                "signal_snapshot": order.metadata.get("signal_snapshot"),
            }
        )

    def _handle_unfilled(self, record: BacktestOrder, simulated: SimulatedFill) -> None:
        order = record.request
        if simulated.status == "cancelled" or order.time_in_force in {"ioc", "fok", "opg", "cls"}:
            record.remaining_quantity = 0.0
            record.transition(self._now(), OrderStatus.CANCELED, simulated.reason)
            return
        record.transition(self._now(), OrderStatus.ACCEPTED, simulated.reason)
        record.ready_index += 1

    def _now(self) -> pd.Timestamp:
        if self.current_timestamp is None:
            raise RuntimeError("BacktestBroker clock is not set.")
        return self.current_timestamp

    def _ready_at(self) -> pd.Timestamp | None:
        if self.current_timestamp is None or self.config.latency_seconds <= 0:
            return None
        return self.current_timestamp + pd.Timedelta(seconds=self.config.latency_seconds)

    def _before_ready_time(self, record: BacktestOrder) -> bool:
        return record.ready_at is not None and self._now() < record.ready_at


SimulatedBroker = BacktestBroker

__all__ = ["BacktestBroker", "BacktestOrder", "OrderStatus", "SimulatedBroker"]
