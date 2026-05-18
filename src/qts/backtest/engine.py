from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from qts.config.models import BacktestConfig
from qts.backtest.execution import BarExecutionSimulator
from qts.backtest.metrics import calculate_performance_metrics
from qts.backtest.portfolio import Portfolio
from qts.risk.manager import RiskManager
from qts.strategies.base import OrderRequest, Strategy, TargetPosition


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]

    def write(self, output_dir: str | Path) -> None:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        self.equity_curve.to_csv(path / "equity_curve.csv", index=False)
        self.trades.to_csv(path / "trades.csv", index=False)
        pd.Series(self.metrics).to_json(path / "metrics.json", indent=2)


@dataclass(frozen=True)
class PendingOrder:
    ready_index: int
    order: OrderRequest
    trail_hwm: float | None = None
    attempts: int = 0


class BacktestEngine:
    def __init__(self, config: BacktestConfig, strategy: Strategy, risk_manager: RiskManager) -> None:
        self.config = config
        self.strategy = strategy
        self.risk_manager = risk_manager

    def run(self, data: pd.DataFrame) -> BacktestResult:
        data = data.sort_values(["timestamp", "symbol"]).reset_index(drop=True)
        if data.empty:
            raise ValueError("Backtest data is empty.")
        portfolio = Portfolio(self.config.initial_cash)
        execution = BarExecutionSimulator(self.config)
        pending_orders: list[PendingOrder] = []
        equity_rows: list[dict[str, object]] = []
        trade_rows: list[dict[str, object]] = []
        entry_state: dict[str, tuple[float, int]] = {}
        session_key = None
        session_start_equity = self.config.initial_cash
        risk_halted = False

        timestamps = list(data["timestamp"].drop_duplicates())
        latest_prices: dict[str, float] = {}
        for index, timestamp in enumerate(timestamps):
            current_session_key = pd.Timestamp(timestamp).date()
            if current_session_key != session_key:
                session_key = current_session_key
                session_start_equity = portfolio.equity(latest_prices) if latest_prices else self.config.initial_cash
                risk_halted = False

            current = data[data["timestamp"] == timestamp]
            latest_prices.update(dict(zip(current["symbol"], current["close"])))

            still_pending: list[PendingOrder] = [item for item in pending_orders if item.ready_index > index]
            ready = [item for item in pending_orders if item.ready_index <= index]
            current_by_symbol = {str(row["symbol"]).upper(): row for _, row in current.iterrows()}
            for pending in ready:
                order = pending.order
                if execution.is_expired(order, pd.Timestamp(timestamp)):
                    continue
                bar = current_by_symbol.get(order.symbol.upper())
                if bar is None:
                    still_pending.append(replace(pending, ready_index=index + 1, attempts=pending.attempts + 1))
                    continue

                simulated = execution.simulate(order, bar, trail_hwm=pending.trail_hwm)
                if not simulated.has_fill:
                    if order.time_in_force not in {"ioc", "fok", "opg", "cls"} and simulated.status != "cancelled":
                        still_pending.append(
                            PendingOrder(
                                ready_index=index + 1,
                                order=order,
                                trail_hwm=simulated.trail_hwm,
                                attempts=pending.attempts + 1,
                            )
                        )
                    continue

                signed_qty = simulated.filled_quantity if order.side == "buy" else -simulated.filled_quantity
                fill_price = execution.apply_slippage(simulated.fill_price, signed_qty)
                commission = execution.commission(simulated.filled_quantity)
                opened_index = entry_state.get(order.symbol, (0.0, index))[1]
                fill = portfolio.apply_fill(order.symbol, signed_qty, fill_price, commission)
                trade_return = None
                holding_period_bars = None
                if fill.realized_pnl is not None:
                    holding_period_bars = index - opened_index
                    trade_return = fill.realized_pnl / (abs(fill.before_average_price * fill.closed_quantity) or 1.0)
                if fill.after_quantity and (
                    not fill.before_quantity or (fill.before_quantity > 0) != (fill.after_quantity > 0)
                ):
                    entry_state[order.symbol] = (fill_price, index)
                elif not fill.after_quantity:
                    entry_state.pop(order.symbol, None)
                trade_rows.append(
                    {
                        "timestamp": timestamp,
                        "symbol": order.symbol,
                        "side": order.side,
                        "quantity": simulated.filled_quantity,
                        "requested_quantity": order.quantity,
                        "remaining_quantity": simulated.remaining_quantity,
                        "order_type": order.order_type,
                        "time_in_force": order.time_in_force,
                        "limit_price": order.limit_price,
                        "stop_price": order.stop_price,
                        "trail_price": order.trail_price,
                        "trail_percent": order.trail_percent,
                        "raw_fill_price": simulated.fill_price,
                        "fill_price": fill_price,
                        "fill_status": simulated.status,
                        "fill_reason": simulated.reason,
                        "fill_bar_open": float(bar["open"]),
                        "fill_bar_high": float(bar["high"]),
                        "fill_bar_low": float(bar["low"]),
                        "fill_bar_close": float(bar["close"]),
                        "fill_bar_vwap": float(bar["vwap"]) if pd.notna(bar.get("vwap")) else None,
                        "fill_bar_volume": float(bar["volume"]),
                        "fill_model": {
                            "market_fill_price": self.config.market_fill_price,
                            "limit_fill_price": self.config.limit_fill_price,
                            "stop_fill_price": self.config.stop_fill_price,
                            "intrabar_price_path": self.config.intrabar_price_path,
                            "max_fill_volume_pct": self.config.max_fill_volume_pct,
                            "allow_partial_fills": self.config.allow_partial_fills,
                            "slippage_bps": self.config.slippage_bps,
                        },
                        "commission": commission,
                        "cash_after": portfolio.cash,
                        "position_after": fill.after_quantity,
                        "average_price_after": fill.after_average_price,
                        "closed_quantity": fill.closed_quantity,
                        "realized_pnl": fill.realized_pnl,
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
                if simulated.remaining_quantity > 1e-9 and order.time_in_force not in {"ioc", "fok", "opg", "cls"}:
                    still_pending.append(
                        PendingOrder(
                            ready_index=index + 1,
                            order=replace(order, quantity=simulated.remaining_quantity),
                            trail_hwm=simulated.trail_hwm,
                            attempts=pending.attempts + 1,
                        )
                    )
            pending_orders = still_pending

            equity_after_fills = portfolio.equity(latest_prices)
            daily_pnl = equity_after_fills - session_start_equity
            if daily_pnl <= -self.risk_manager.config.max_daily_loss:
                risk_halted = True

            if risk_halted or self.risk_manager.config.kill_switch:
                targets = [
                    TargetPosition(timestamp=timestamp.to_pydatetime(), symbol=symbol, target_fraction=0.0)
                    for symbol, position in portfolio.positions.items()
                    if abs(position.quantity) > 1e-9
                ]
            else:
                history = data[data["timestamp"] <= timestamp]
                targets = self.risk_manager.validate_targets(self.strategy.generate_targets(history, timestamp))
            pending_quantities: dict[str, float] = {}
            for pending in pending_orders:
                pending_order = pending.order
                signed = pending_order.quantity if pending_order.side == "buy" else -pending_order.quantity
                pending_quantities[pending_order.symbol] = pending_quantities.get(pending_order.symbol, 0.0) + signed

            orders = portfolio.orders_for_targets(
                targets,
                latest_prices,
                timestamp,
                max_position_notional=self.risk_manager.config.max_position_notional,
                pending_quantities=pending_quantities,
            )
            orders = self.risk_manager.validate_orders(orders, latest_prices, timestamp)
            pending_orders.extend(
                PendingOrder(index + max(self.config.latency_bars, 0), order)
                for order in orders
            )

            equity = portfolio.equity(latest_prices)
            gross_exposure = (
                sum(abs(pos.quantity * latest_prices.get(symbol, pos.average_price)) for symbol, pos in portfolio.positions.items()) / equity
                if equity
                else 0.0
            )
            equity_rows.append(
                {
                    "timestamp": timestamp,
                    "cash": portfolio.cash,
                    "market_value": portfolio.market_value(latest_prices),
                    "equity": equity,
                    "gross_exposure": gross_exposure,
                    "daily_pnl": daily_pnl,
                    "risk_halted": risk_halted,
                    "pending_orders": len(pending_orders),
                }
            )

        equity_curve = pd.DataFrame(equity_rows)
        trades = pd.DataFrame(trade_rows)
        metrics = calculate_performance_metrics(equity_curve, trades, self.config.annualization_periods)
        return BacktestResult(equity_curve=equity_curve, trades=trades, metrics=metrics)
