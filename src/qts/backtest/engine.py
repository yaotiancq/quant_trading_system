from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from qts.config.models import BacktestConfig
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
        pending_orders: list[tuple[int, OrderRequest]] = []
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

            ready = [item for item in pending_orders if item[0] <= index]
            pending_orders = [item for item in pending_orders if item[0] > index]
            for _, order in ready:
                if order.symbol not in latest_prices:
                    continue
                signed_qty = order.quantity if order.side == "buy" else -order.quantity
                raw_price = latest_prices[order.symbol]
                fill_price = raw_price * (1 + self.config.slippage_bps / 10_000 * (1 if signed_qty > 0 else -1))
                commission = abs(order.quantity) * self.config.commission_per_share
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
                        "quantity": order.quantity,
                        "fill_price": fill_price,
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

            equity_after_fills = portfolio.equity(latest_prices)
            daily_pnl = equity_after_fills - session_start_equity
            if daily_pnl <= -self.risk_manager.config.max_daily_loss:
                risk_halted = True

            if risk_halted:
                targets = [
                    TargetPosition(timestamp=timestamp.to_pydatetime(), symbol=symbol, target_fraction=0.0)
                    for symbol, position in portfolio.positions.items()
                    if abs(position.quantity) > 1e-9
                ]
            else:
                history = data[data["timestamp"] <= timestamp]
                targets = self.risk_manager.validate_targets(self.strategy.generate_targets(history, timestamp))
            orders = portfolio.orders_for_targets(
                targets,
                latest_prices,
                timestamp,
                max_position_notional=self.risk_manager.config.max_position_notional,
            )
            pending_orders.extend((index + max(self.config.latency_bars, 0), order) for order in orders)

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
                }
            )

        equity_curve = pd.DataFrame(equity_rows)
        trades = pd.DataFrame(trade_rows)
        metrics = calculate_performance_metrics(equity_curve, trades, self.config.annualization_periods)
        return BacktestResult(equity_curve=equity_curve, trades=trades, metrics=metrics)
