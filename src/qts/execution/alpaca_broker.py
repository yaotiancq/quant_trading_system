from __future__ import annotations

from dataclasses import dataclass

from qts.backtest.orders import OrderRequest, OrderSide
from qts.config.loader import EnvSettings


@dataclass(frozen=True)
class AlpacaBrokerConfig:
    paper: bool = True
    live_trading_enabled: bool = False


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

    def get_open_orders(self) -> list[object]:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus

        return list(self.client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN)))

    def get_cash(self) -> float:
        return float(getattr(self.get_account(), "cash", 0.0))

    def submit_order(self, order: OrderRequest) -> object:
        from alpaca.trading.enums import OrderClass, OrderSide as AlpacaOrderSide, OrderType as AlpacaOrderType, TimeInForce
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
            "side": AlpacaOrderSide.BUY if order.side in {OrderSide.BUY, OrderSide.BUY_TO_COVER} else AlpacaOrderSide.SELL,
            "time_in_force": TimeInForce(order.time_in_force),
            "extended_hours": order.extended_hours,
        }
        if order.order_class:
            base["order_class"] = OrderClass(order.order_class)

        order_type = AlpacaOrderType(order.order_type.value)
        if order_type == AlpacaOrderType.MARKET:
            request = MarketOrderRequest(type=order_type, **base)
        elif order_type == AlpacaOrderType.LIMIT:
            if order.limit_price is None:
                raise ValueError("Limit orders require limit_price.")
            request = LimitOrderRequest(type=order_type, limit_price=order.limit_price, **base)
        elif order_type == AlpacaOrderType.STOP:
            if order.stop_price is None:
                raise ValueError("Stop orders require stop_price.")
            request = StopOrderRequest(type=order_type, stop_price=order.stop_price, **base)
        elif order_type == AlpacaOrderType.STOP_LIMIT:
            if order.stop_price is None or order.limit_price is None:
                raise ValueError("Stop-limit orders require stop_price and limit_price.")
            request = StopLimitOrderRequest(
                type=order_type,
                stop_price=order.stop_price,
                limit_price=order.limit_price,
                **base,
            )
        elif order_type == AlpacaOrderType.TRAILING_STOP:
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


class AlpacaPaperBroker(AlpacaBrokerAdapter):
    def __init__(self, settings: EnvSettings) -> None:
        super().__init__(settings, paper=True, live_trading_enabled=False)


class AlpacaLiveBroker(AlpacaBrokerAdapter):
    def __init__(self, settings: EnvSettings, live_trading_enabled: bool = False) -> None:
        if not live_trading_enabled:
            raise ValueError("Alpaca live trading is disabled by default. Set live_trading_enabled=true explicitly.")
        super().__init__(settings, paper=False, live_trading_enabled=True)
