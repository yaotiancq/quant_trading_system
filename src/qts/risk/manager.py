from __future__ import annotations

from dataclasses import replace
from datetime import datetime, time

import pandas as pd

from qts.config.models import RiskConfig
from qts.strategies.base import OrderRequest, TargetPosition


class RiskManager:
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
    ) -> list[OrderRequest]:
        if self.config.kill_switch or not self.is_trading_session_open(timestamp):
            return []

        approved: list[OrderRequest] = []
        for order in orders:
            price = latest_prices.get(order.symbol.upper())
            if price is None or price <= 0:
                continue

            max_quantity_by_notional = self.config.max_order_notional / price
            max_quantity = min(self.config.max_position_quantity, max_quantity_by_notional)
            quantity = min(order.quantity, max_quantity)
            if quantity <= 1e-9:
                continue

            metadata = {
                **order.metadata,
                "risk_max_order_notional": self.config.max_order_notional,
                "risk_max_position_quantity": self.config.max_position_quantity,
                "risk_reference_price": price,
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


def _parse_time(value: str) -> time:
    try:
        parsed = datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise ValueError(f"Trading session time must use HH:MM format, got {value!r}.") from exc
    return parsed
