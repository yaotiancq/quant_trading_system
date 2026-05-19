from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from qts.backtest.orders import OrderSide
from qts.config.models import BacktestConfig
from qts.backtest.orders import OrderRequest


@dataclass(frozen=True)
class SimulatedFill:
    filled_quantity: float
    fill_price: float | None
    status: str
    reason: str
    remaining_quantity: float
    trail_hwm: float | None = None

    @property
    def has_fill(self) -> bool:
        return self.filled_quantity > 0 and self.fill_price is not None


class BarExecutionSimulator:
    """Simulate Alpaca-style order types against one OHLCV bar.

    OHLCV bars do not reveal the true trade sequence, queue priority, spread, or depth.
    The simulator therefore uses explicit, configurable assumptions rather than treating
    the bar close as the universal execution price.
    """

    SUPPORTED_ORDER_TYPES = {"market", "limit", "stop", "stop_limit", "trailing_stop"}
    SUPPORTED_TIF = {"day", "gtc", "opg", "cls", "ioc", "fok"}

    def __init__(self, config: BacktestConfig) -> None:
        self.config = config

    def simulate(
        self,
        order: OrderRequest,
        bar: pd.Series,
        trail_hwm: float | None = None,
    ) -> SimulatedFill:
        order_type = order.order_type.lower()
        tif = order.time_in_force.lower()
        if order_type not in self.SUPPORTED_ORDER_TYPES:
            return _no_fill(order, f"unsupported_order_type:{order.order_type}", trail_hwm)
        if tif not in self.SUPPORTED_TIF:
            return _no_fill(order, f"unsupported_time_in_force:{order.time_in_force}", trail_hwm)

        raw_price: float | None
        reason: str
        next_hwm = trail_hwm
        if order_type == "market":
            raw_price = self._market_price(bar, tif)
            reason = f"market_{self._market_price_source(tif)}"
        elif order_type == "limit":
            raw_price = self._limit_price(order, bar, tif)
            reason = "limit_touched" if raw_price is not None else "limit_not_touched"
        elif order_type == "stop":
            raw_price = self._stop_price(order, bar, tif)
            reason = "stop_triggered" if raw_price is not None else "stop_not_triggered"
        elif order_type == "stop_limit":
            raw_price = self._stop_limit_price(order, bar, tif)
            reason = "stop_limit_triggered_and_executable" if raw_price is not None else "stop_limit_not_executable"
        else:
            raw_price, next_hwm = self._trailing_stop_price(order, bar, tif, trail_hwm)
            reason = "trailing_stop_triggered" if raw_price is not None else "trailing_stop_not_triggered"

        if raw_price is None:
            return _no_fill(order, reason, next_hwm)

        quantity = self._fillable_quantity(order, bar)
        if quantity <= 0:
            return _no_fill(order, "insufficient_bar_volume", next_hwm)
        if tif == "fok" and quantity < order.quantity:
            return SimulatedFill(
                filled_quantity=0.0,
                fill_price=None,
                status="cancelled",
                reason="fok_not_fully_fillable",
                remaining_quantity=0.0,
                trail_hwm=next_hwm,
            )

        remaining = max(order.quantity - quantity, 0.0)
        if tif in {"ioc", "opg", "cls"}:
            remaining = 0.0
        status = "filled" if remaining <= 1e-9 else "partially_filled"
        return SimulatedFill(
            filled_quantity=quantity,
            fill_price=float(raw_price),
            status=status,
            reason=reason,
            remaining_quantity=remaining,
            trail_hwm=next_hwm,
        )

    def is_expired(self, order: OrderRequest, timestamp: pd.Timestamp) -> bool:
        if order.time_in_force.lower() != "day":
            return False
        return pd.Timestamp(timestamp).date() > pd.Timestamp(order.timestamp).date()

    def apply_slippage(self, price: float, signed_quantity: float) -> float:
        direction = 1 if signed_quantity > 0 else -1
        return price * (1 + direction * self.config.slippage_bps / 10_000)

    def commission(self, quantity: float, fill_price: float) -> float:
        per_share = abs(quantity) * self.config.commission_per_share
        notional_bps = abs(quantity * fill_price) * self.config.commission_bps / 10_000
        fixed = self.config.fixed_commission if quantity else 0.0
        return per_share + notional_bps + fixed

    def _market_price(self, bar: pd.Series, tif: str) -> float:
        source = self._market_price_source(tif)
        if source == "open":
            return float(bar["open"])
        if source == "close":
            return float(bar["close"])
        if source == "hlc3":
            return float((bar["high"] + bar["low"] + bar["close"]) / 3.0)
        if source == "ohlc4":
            return float((bar["open"] + bar["high"] + bar["low"] + bar["close"]) / 4.0)
        if source == "vwap" and pd.notna(bar.get("vwap")):
            return float(bar["vwap"])
        return float(bar["open"])

    def _market_price_source(self, tif: str) -> str:
        if tif == "opg":
            return "open"
        if tif == "cls":
            return "close"
        return self.config.market_fill_price

    def _limit_price(self, order: OrderRequest, bar: pd.Series, tif: str) -> float | None:
        if order.limit_price is None:
            return None
        limit = float(order.limit_price)
        previous_price = None
        for index, price in enumerate(self._price_path(bar, tif)):
            if _limit_accepts(order.side, price, limit):
                if index == 0:
                    return price
                return self._limit_touch_price(order.side, limit, previous_price, price)
            previous_price = price
        return None

    def _stop_price(self, order: OrderRequest, bar: pd.Series, tif: str) -> float | None:
        if order.stop_price is None:
            return None
        stop = float(order.stop_price)
        trigger = self._first_stop_trigger(order.side, stop, self._price_path(bar, tif))
        if trigger is None:
            return None
        trigger_price, index = trigger
        if self.config.stop_fill_price == "market":
            return trigger_price
        if index == 0:
            return trigger_price
        return stop

    def _stop_limit_price(self, order: OrderRequest, bar: pd.Series, tif: str) -> float | None:
        if order.stop_price is None or order.limit_price is None:
            return None
        stop = float(order.stop_price)
        limit = float(order.limit_price)
        path = self._price_path(bar, tif)
        triggered = False
        previous_price = None
        for index, price in enumerate(path):
            if not triggered:
                trigger = self._stop_trigger_at_path_price(order.side, stop, price, index)
                if trigger is None:
                    previous_price = price
                    continue
                triggered = True
                trigger_price = trigger
                if _limit_accepts(order.side, trigger_price, limit):
                    return trigger_price
                previous_price = trigger_price
                continue
            if _limit_accepts(order.side, price, limit):
                return self._limit_touch_price(order.side, limit, previous_price, price)
            previous_price = price
        return None

    def _limit_touch_price(
        self,
        side: OrderSide | str,
        limit: float,
        previous_price: float | None,
        touch_price: float,
    ) -> float:
        if self.config.limit_fill_price == "touch":
            return limit
        if self.config.limit_fill_price == "midpoint" and previous_price is not None:
            return min(limit, (previous_price + touch_price) / 2.0) if _is_buy_side(side) else max(limit, (previous_price + touch_price) / 2.0)
        return limit

    def _first_stop_trigger(
        self,
        side: OrderSide | str,
        stop: float,
        path: list[float],
    ) -> tuple[float, int] | None:
        for index, price in enumerate(path):
            trigger_price = self._stop_trigger_at_path_price(side, stop, price, index)
            if trigger_price is not None:
                return trigger_price, index
        return None

    def _stop_trigger_at_path_price(
        self,
        side: OrderSide | str,
        stop: float,
        price: float,
        index: int,
    ) -> float | None:
        if _is_buy_side(side) and price >= stop:
            return max(stop, price) if index == 0 else stop
        if _is_sell_side(side) and price <= stop:
            return min(stop, price) if index == 0 else stop
        return None

    def _trailing_stop_price(
        self,
        order: OrderRequest,
        bar: pd.Series,
        tif: str,
        trail_hwm: float | None,
    ) -> tuple[float | None, float | None]:
        if order.trail_price is None and order.trail_percent is None:
            return None, trail_hwm

        path = self._price_path(bar, tif)
        hwm = float(trail_hwm if trail_hwm is not None else path[0])
        if _is_sell_side(order.side):
            hwm = max(hwm, path[0])
            for price in path:
                hwm = max(hwm, price)
                stop = _trailing_stop_from_hwm(hwm, order)
                if price <= stop:
                    return stop if self.config.stop_fill_price == "stop" else min(stop, price), hwm
        else:
            hwm = min(hwm, path[0])
            for price in path:
                hwm = min(hwm, price)
                stop = _trailing_stop_from_hwm(hwm, order)
                if price >= stop:
                    return stop if self.config.stop_fill_price == "stop" else max(stop, price), hwm
        return None, hwm

    def _stop_trigger_price(self, side: str, stop: float, bar: pd.Series, tif: str) -> float | None:
        if tif == "opg":
            open_price = float(bar["open"])
            if _is_buy_side(side) and open_price >= stop:
                return max(stop, open_price)
            if _is_sell_side(side) and open_price <= stop:
                return min(stop, open_price)
            return None
        if tif == "cls":
            close_price = float(bar["close"])
            if _is_buy_side(side) and close_price >= stop:
                return max(stop, close_price)
            if _is_sell_side(side) and close_price <= stop:
                return min(stop, close_price)
            return None

        open_price = float(bar["open"])
        if _is_buy_side(side):
            if open_price >= stop:
                return max(stop, open_price)
            return stop if float(bar["high"]) >= stop else None
        if open_price <= stop:
            return min(stop, open_price)
        return stop if float(bar["low"]) <= stop else None

    def _price_path(self, bar: pd.Series, tif: str) -> list[float]:
        if tif == "opg":
            return [float(bar["open"])]
        if tif == "cls":
            return [float(bar["close"])]
        if self.config.intrabar_price_path == "open_low_high_close":
            return [float(bar["open"]), float(bar["low"]), float(bar["high"]), float(bar["close"])]
        return [float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])]

    def _fillable_quantity(self, order: OrderRequest, bar: pd.Series) -> float:
        volume = float(bar.get("volume", 0.0) or 0.0)
        if volume <= 0:
            return order.quantity if not self.config.allow_partial_fills else 0.0
        max_quantity = volume * self.config.max_fill_volume_pct
        if order.quantity <= max_quantity:
            return order.quantity
        return max_quantity if self.config.allow_partial_fills else 0.0


def apply_slippage(price: float, signed_quantity: float, slippage_bps: float) -> float:
    direction = 1 if signed_quantity > 0 else -1
    return price * (1 + direction * slippage_bps / 10_000)


def per_share_commission(quantity: float, commission_per_share: float) -> float:
    return abs(quantity) * commission_per_share


def _limit_accepts(side: str, price: float, limit: float) -> bool:
    return price <= limit if _is_buy_side(side) else price >= limit


def _trailing_stop_from_hwm(hwm: float, order: OrderRequest) -> float:
    if order.trail_price is not None:
        trail = float(order.trail_price)
        return hwm - trail if _is_sell_side(order.side) else hwm + trail
    trail_percent = float(order.trail_percent or 0.0) / 100.0
    return hwm * (1 - trail_percent) if _is_sell_side(order.side) else hwm * (1 + trail_percent)


def _is_buy_side(side: OrderSide | str) -> bool:
    return side in {OrderSide.BUY, OrderSide.BUY_TO_COVER, "buy", "buy_to_cover"}


def _is_sell_side(side: OrderSide | str) -> bool:
    return side in {OrderSide.SELL, OrderSide.SELL_SHORT, "sell", "sell_short"}


def _no_fill(order: OrderRequest, reason: str, trail_hwm: float | None) -> SimulatedFill:
    return SimulatedFill(
        filled_quantity=0.0,
        fill_price=None,
        status="unfilled",
        reason=reason,
        remaining_quantity=order.quantity,
        trail_hwm=trail_hwm,
    )


ExecutionSimulator = BarExecutionSimulator

__all__ = [
    "BarExecutionSimulator",
    "ExecutionSimulator",
    "SimulatedFill",
    "apply_slippage",
    "per_share_commission",
]
