from __future__ import annotations

from typing import Protocol

from qts.strategies.base import OrderRequest


class BrokerAdapter(Protocol):
    def get_account(self) -> object: ...

    def get_positions(self) -> list[object]: ...

    def get_clock(self) -> object: ...

    def submit_order(self, order: OrderRequest) -> object: ...

    def cancel_order(self, order_id: str) -> None: ...

    def get_order_status(self, order_id: str) -> object: ...

