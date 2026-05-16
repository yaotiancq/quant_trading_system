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
        from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        request = MarketOrderRequest(
            symbol=order.symbol,
            qty=order.quantity,
            side=OrderSide.BUY if order.side == "buy" else OrderSide.SELL,
            type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
        )
        return self.client.submit_order(request)

    def cancel_order(self, order_id: str) -> None:
        self.client.cancel_order_by_id(order_id)

    def get_order_status(self, order_id: str) -> object:
        return self.client.get_order_by_id(order_id)

