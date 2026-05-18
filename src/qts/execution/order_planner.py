from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from enum import Enum

import pandas as pd
import numpy as np

from qts.backtest.orders import OrderRequest, OrderSide
from qts.signals.base import TradingSignal
from qts.strategies.base import TargetPosition


def plan_orders_from_targets(
    targets: Sequence[TargetPosition],
    equity: float,
    current_quantities: Mapping[str, float],
    latest_prices: Mapping[str, float],
    timestamp: datetime | pd.Timestamp,
    max_position_notional: float,
    min_quantity: float = 1e-9,
    strategy_id: str | None = None,
) -> list[OrderRequest]:
    if equity <= 0:
        return []

    normalized_quantities = {symbol.upper(): quantity for symbol, quantity in current_quantities.items()}
    normalized_prices = {symbol.upper(): price for symbol, price in latest_prices.items()}
    order_timestamp = _to_datetime(timestamp)
    orders: list[OrderRequest] = []

    for target in targets:
        symbol = target.symbol.upper()
        price = normalized_prices.get(symbol)
        if price is None or price <= 0:
            continue

        target_notional = target.target_fraction * equity
        capped_notional = max(min(target_notional, max_position_notional), -max_position_notional)
        desired_quantity = capped_notional / price
        current_quantity = normalized_quantities.get(symbol, 0.0)
        delta_quantity = desired_quantity - current_quantity
        if abs(delta_quantity) <= min_quantity:
            continue

        side = _order_side_for_delta(delta_quantity, current_quantity)
        limit_price = _optional_float(target.metadata.get("limit_price"))
        stop_price = _optional_float(target.metadata.get("stop_price"))
        if limit_price is None:
            limit_price = _offset_price(target.metadata.get("limit_price_offset_bps"), price, side, price_type="limit")
        if stop_price is None:
            stop_price = _offset_price(target.metadata.get("stop_price_offset_bps"), price, side, price_type="stop")

        orders.append(
            OrderRequest(
                timestamp=order_timestamp,
                symbol=symbol,
                side=side,
                quantity=abs(delta_quantity),
                order_type=str(target.metadata.get("order_type", "market")),
                time_in_force=str(target.metadata.get("time_in_force", "day")),
                limit_price=limit_price,
                stop_price=stop_price,
                trail_price=_optional_float(target.metadata.get("trail_price")),
                trail_percent=_optional_float(target.metadata.get("trail_percent")),
                extended_hours=bool(target.metadata.get("extended_hours", False)),
                order_class=str(target.metadata["order_class"]) if target.metadata.get("order_class") else None,
                strategy_id=str(target.metadata.get("strategy_id", strategy_id)) if target.metadata.get("strategy_id", strategy_id) else None,
                metadata={
                    "target_fraction": target.target_fraction,
                    "target_notional": capped_notional,
                    "current_quantity": current_quantity,
                    "desired_quantity": desired_quantity,
                    "reference_price": price,
                    **_signal_order_metadata(target.metadata),
                },
            )
        )
    return orders


def broker_position_quantities(positions: Iterable[object]) -> dict[str, float]:
    quantities: dict[str, float] = {}
    for position in positions:
        symbol = str(getattr(position, "symbol")).upper()
        quantities[symbol] = float(getattr(position, "qty", getattr(position, "quantity", 0.0)))
    return quantities


def _order_side_for_delta(delta_quantity: float, current_quantity: float) -> OrderSide:
    if delta_quantity > 0:
        return OrderSide.BUY_TO_COVER if current_quantity < 0 else OrderSide.BUY
    return OrderSide.SELL if current_quantity > 0 else OrderSide.SELL_SHORT


def _to_datetime(value: datetime | pd.Timestamp) -> datetime:
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


def _signal_order_metadata(metadata: Mapping[str, object]) -> dict[str, object]:
    signal = metadata.get("signal")
    signal_snapshot = metadata.get("signal_snapshot")
    if isinstance(signal, TradingSignal):
        signal_snapshot = signal.to_dict()
    provenance = metadata.get("signal_provenance")
    if isinstance(signal, TradingSignal) and signal.provenance:
        provenance = signal.provenance.to_dict()
    if not isinstance(signal_snapshot, dict):
        signal_snapshot = None
    if not isinstance(provenance, dict):
        provenance = None

    result: dict[str, object] = {
        "target_metadata": _json_safe({k: v for k, v in metadata.items() if k != "signal"}),
        "signal_snapshot": _json_safe(signal_snapshot),
        "signal_provenance": _json_safe(provenance),
    }
    if isinstance(signal, TradingSignal):
        result.update(
            {
                "signal_type": signal.signal_type.value,
                "signal_direction": signal.direction.value,
                "signal_strength": signal.strength,
                "signal_confidence": signal.confidence,
                "signal_confidence_metadata": _json_safe(signal.confidence_metadata),
            }
        )
    if provenance:
        result.update(
            {
                "signal_source_name": provenance.get("source_name"),
                "signal_source_type": provenance.get("source_type"),
                "signal_model_version": provenance.get("model_version"),
                "signal_feature_set": provenance.get("feature_set"),
            }
        )
    return result


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _offset_price(value: object, reference_price: float, side: str, price_type: str) -> float | None:
    if value is None:
        return None
    offset = float(value) / 10_000
    is_buy = side in {OrderSide.BUY, OrderSide.BUY_TO_COVER, "buy", "buy_to_cover"}
    if price_type == "limit":
        multiplier = 1 - offset if is_buy else 1 + offset
    else:
        multiplier = 1 + offset if is_buy else 1 - offset
    return reference_price * multiplier


def _json_safe(value: object) -> object:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, TradingSignal):
        return value.to_dict()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value
