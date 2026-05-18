from __future__ import annotations

from qts.config.loader import EnvSettings
from qts.strategies.base import OrderRequest


class AlpacaBrokerAdapter:
    def __init__(self, settings: EnvSettings, paper: bool = True, live_trading_enabled: bool = False) -> None:
        if not paper and not live_trading_enabled:
            raise ValueError("Live trading is disabled. Set live_trading_enabled=true explicitly to construct a live adapter.")
        if not settings.alpaca_api_key_id or not settings.alpaca_api_secret_key:
            raise ValueError("Alpaca API credentials are required in environment variables.")
        from alpaca.trading.client import TradingClient

        self.client = TradingClient(settings.alpaca_api_key_id, settings.alpaca_api_secret_key, paper=paper)

    def get_account(self) -> object:
        return self.client.get_account()

    def get_positions(self) -> list[object]:
        return list(self.client.get_all_positions())

    def get_clock(self) -> object:
        return self.client.get_clock()

    def submit_order(self, order: OrderRequest) -> object:
        from alpaca.trading.enums import OrderClass, OrderSide, OrderType, TimeInForce
        from alpaca.trading.requests import (
            LimitOrderRequest,
            MarketOrderRequest,
            StopLimitOrderRequest,
            StopOrderRequest,
            TrailingStopOrderRequest,
        )

        base = {
            "symbol": order.symbol,
            "qty": order.quantity,
            "side": OrderSide.BUY if order.side == "buy" else OrderSide.SELL,
            "time_in_force": TimeInForce(order.time_in_force),
            "extended_hours": order.extended_hours,
        }
        if order.order_class:
            base["order_class"] = OrderClass(order.order_class)

        order_type = OrderType(order.order_type)
        if order_type == OrderType.MARKET:
            request = MarketOrderRequest(type=order_type, **base)
        elif order_type == OrderType.LIMIT:
            if order.limit_price is None:
                raise ValueError("Limit orders require limit_price.")
            request = LimitOrderRequest(type=order_type, limit_price=order.limit_price, **base)
        elif order_type == OrderType.STOP:
            if order.stop_price is None:
                raise ValueError("Stop orders require stop_price.")
            request = StopOrderRequest(type=order_type, stop_price=order.stop_price, **base)
        elif order_type == OrderType.STOP_LIMIT:
            if order.stop_price is None or order.limit_price is None:
                raise ValueError("Stop-limit orders require stop_price and limit_price.")
            request = StopLimitOrderRequest(
                type=order_type,
                stop_price=order.stop_price,
                limit_price=order.limit_price,
                **base,
            )
        elif order_type == OrderType.TRAILING_STOP:
            if order.trail_price is None and order.trail_percent is None:
                raise ValueError("Trailing-stop orders require trail_price or trail_percent.")
            request = TrailingStopOrderRequest(
                type=order_type,
                trail_price=order.trail_price,
                trail_percent=order.trail_percent,
                **base,
            )
        else:
            raise ValueError(f"Unsupported order type: {order.order_type}")

        return self.client.submit_order(request)

    def cancel_order(self, order_id: str) -> None:
        self.client.cancel_order_by_id(order_id)

    def get_order_status(self, order_id: str) -> object:
        return self.client.get_order_by_id(order_id)
