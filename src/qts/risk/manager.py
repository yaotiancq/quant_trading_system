from __future__ import annotations

from dataclasses import replace
from datetime import datetime, time

import pandas as pd

from qts.config.models import RiskConfig
from qts.backtest.orders import OrderRequest, OrderSide, OrderType
from qts.strategies.base import TargetPosition


class RiskManager:
    SUPPORTED_ORDER_TYPES = {"market", "limit", "stop", "stop_limit", "trailing_stop"}
    SUPPORTED_TIME_IN_FORCE = {"day", "gtc", "opg", "cls", "ioc", "fok"}

    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def validate_targets(self, targets: list[TargetPosition]) -> list[TargetPosition]:
        if self.config.kill_switch:
            return []
        approved: list[TargetPosition] = []
        gross = 0.0
        for target in targets:
            if target.target_fraction < 0 and not self.config.allow_short:
                clipped = 0.0
            else:
                clipped = max(min(target.target_fraction, self.config.max_symbol_exposure), -self.config.max_symbol_exposure)
            gross += abs(clipped)
            approved.append(
                TargetPosition(
                    timestamp=target.timestamp,
                    symbol=target.symbol,
                    target_fraction=clipped,
                    metadata=target.metadata,
                )
            )
        if gross <= self.config.max_gross_exposure:
            return approved
        scale = self.config.max_gross_exposure / gross if gross else 0.0
        return [
            TargetPosition(t.timestamp, t.symbol, t.target_fraction * scale, t.metadata)
            for t in approved
        ]

    def validate_orders(
        self,
        orders: list[OrderRequest],
        latest_prices: dict[str, float],
        timestamp: datetime | pd.Timestamp,
        *,
        current_quantities: dict[str, float] | None = None,
    ) -> list[OrderRequest]:
        return self._validate_orders(
            orders,
            latest_prices,
            timestamp,
            current_quantities=current_quantities,
            bypass_size_limits=False,
            ignore_kill_switch=False,
            ignore_session=False,
        )

    def validate_liquidation_orders(
        self,
        orders: list[OrderRequest],
        latest_prices: dict[str, float],
        timestamp: datetime | pd.Timestamp,
        *,
        current_quantities: dict[str, float] | None = None,
    ) -> list[OrderRequest]:
        return self._validate_orders(
            orders,
            latest_prices,
            timestamp,
            current_quantities=current_quantities,
            bypass_size_limits=True,
            ignore_kill_switch=True,
            ignore_session=True,
            liquidation=True,
        )

    def _validate_orders(
        self,
        orders: list[OrderRequest],
        latest_prices: dict[str, float],
        timestamp: datetime | pd.Timestamp,
        *,
        current_quantities: dict[str, float] | None,
        bypass_size_limits: bool,
        ignore_kill_switch: bool,
        ignore_session: bool,
        liquidation: bool = False,
    ) -> list[OrderRequest]:
        if (self.config.kill_switch and not ignore_kill_switch) or (
            not ignore_session and not self.is_trading_session_open(timestamp)
        ):
            return []

        normalized_quantities = {symbol.upper(): quantity for symbol, quantity in (current_quantities or {}).items()}
        approved: list[OrderRequest] = []
        for order in orders:
            normalized_order = self._normalize_and_validate_order(order)
            if normalized_order is None:
                continue
            order = normalized_order
            price = latest_prices.get(order.symbol.upper())
            if price is None or price <= 0:
                continue

            if order.side == OrderSide.SELL_SHORT and not self.config.allow_short:
                continue
            requested_quantity = float(order.quantity or ((order.notional or 0.0) / price))
            side_cap = _side_quantity_cap(order, normalized_quantities)
            if side_cap <= 1e-9:
                continue
            if bypass_size_limits:
                max_quantity = requested_quantity
            else:
                max_quantity_by_notional = self.config.max_order_notional / price
                max_quantity = min(self.config.max_position_quantity, max_quantity_by_notional)
            quantity = min(requested_quantity, max_quantity, side_cap)
            if quantity <= 1e-9:
                continue

            metadata = {
                **order.metadata,
                "risk_max_order_notional": self.config.max_order_notional,
                "risk_max_position_quantity": self.config.max_position_quantity,
                "risk_reference_price": price,
                "risk_bypassed_size_limits": bypass_size_limits,
                "risk_liquidation_order": liquidation,
            }
            approved.append(replace(order, quantity=quantity, metadata=metadata))
        return approved

    def is_trading_session_open(self, timestamp: datetime | pd.Timestamp) -> bool:
        if not self.config.trading_session_start or not self.config.trading_session_end:
            return True

        current = pd.Timestamp(timestamp)
        start = _parse_time(self.config.trading_session_start)
        end = _parse_time(self.config.trading_session_end)
        current_time = current.time()
        if start <= end:
            return start <= current_time <= end
        return current_time >= start or current_time <= end

    def _normalize_and_validate_order(self, order: OrderRequest) -> OrderRequest | None:
        order_type = order.order_type.value
        tif = order.time_in_force.lower()
        if order_type not in self.SUPPORTED_ORDER_TYPES or tif not in self.SUPPORTED_TIME_IN_FORCE:
            return None
        if order.extended_hours and not (order_type == "limit" and tif in {"day", "gtc"}):
            return None
        if tif in {"opg", "cls", "ioc", "fok"} and order_type not in {"market", "limit"}:
            return None
        if order_type in {"stop", "stop_limit", "trailing_stop"} and tif not in {"day", "gtc"}:
            return None
        if order_type == "limit" and order.limit_price is None:
            return None
        if order_type == "stop" and order.stop_price is None:
            return None
        if order_type == "stop_limit" and (order.stop_price is None or order.limit_price is None):
            return None
        if order_type == "trailing_stop" and order.trail_price is None and order.trail_percent is None:
            return None
        return replace(order, order_type=OrderType(order_type), time_in_force=tif, symbol=order.symbol.upper())


def _parse_time(value: str) -> time:
    try:
        parsed = datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise ValueError(f"Trading session time must use HH:MM format, got {value!r}.") from exc
    return parsed


def _side_quantity_cap(order: OrderRequest, current_quantities: dict[str, float]) -> float:
    if not current_quantities:
        return float("inf")
    current_quantity = current_quantities.get(order.symbol.upper(), 0.0)
    if order.side == OrderSide.SELL:
        return max(current_quantity, 0.0)
    if order.side == OrderSide.BUY_TO_COVER:
        return max(-current_quantity, 0.0)
    return float("inf")
