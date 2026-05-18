"""Backtesting package exports.

Exports are loaded lazily so shared models such as ``qts.backtest.orders`` can be
imported by strategy, risk, and execution modules without pulling in the full
engine dependency graph.
"""

from __future__ import annotations

__all__ = [
    "BacktestBroker",
    "BacktestEngine",
    "BacktestOrder",
    "BacktestResult",
    "BarExecutionSimulator",
    "ExecutionSimulator",
    "FillEvent",
    "FillResult",
    "OrderRequest",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "Portfolio",
    "SimulatedBroker",
    "calculate_performance_metrics",
]


def __getattr__(name: str) -> object:
    if name in {"BacktestBroker", "BacktestOrder", "SimulatedBroker"}:
        from qts.backtest.broker import BacktestBroker, BacktestOrder, SimulatedBroker

        return {
            "BacktestBroker": BacktestBroker,
            "BacktestOrder": BacktestOrder,
            "SimulatedBroker": SimulatedBroker,
        }[name]
    if name in {"BacktestEngine", "BacktestResult"}:
        from qts.backtest.engine import BacktestEngine, BacktestResult

        return {"BacktestEngine": BacktestEngine, "BacktestResult": BacktestResult}[name]
    if name in {"BarExecutionSimulator", "ExecutionSimulator"}:
        from qts.backtest.execution import BarExecutionSimulator, ExecutionSimulator

        return {
            "BarExecutionSimulator": BarExecutionSimulator,
            "ExecutionSimulator": ExecutionSimulator,
        }[name]
    if name == "FillEvent":
        from qts.backtest.fills import FillEvent

        return FillEvent
    if name == "calculate_performance_metrics":
        from qts.backtest.metrics import calculate_performance_metrics

        return calculate_performance_metrics
    if name in {"OrderRequest", "OrderSide", "OrderStatus", "OrderType"}:
        from qts.backtest.orders import OrderRequest, OrderSide, OrderStatus, OrderType

        return {
            "OrderRequest": OrderRequest,
            "OrderSide": OrderSide,
            "OrderStatus": OrderStatus,
            "OrderType": OrderType,
        }[name]
    if name in {"FillResult", "Portfolio"}:
        from qts.backtest.portfolio import FillResult, Portfolio

        return {"FillResult": FillResult, "Portfolio": Portfolio}[name]
    raise AttributeError(name)
