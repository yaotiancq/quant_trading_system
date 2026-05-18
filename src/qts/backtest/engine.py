from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from qts.backtest.broker import BacktestBroker
from qts.backtest.metrics import calculate_performance_metrics
from qts.config.models import BacktestConfig
from qts.risk.manager import RiskManager
from qts.strategies.base import Strategy


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    orders: pd.DataFrame
    order_events: pd.DataFrame
    metrics: dict[str, float]

    def write(self, output_dir: str | Path) -> None:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        self.equity_curve.to_csv(path / "equity_curve.csv", index=False)
        self.trades.to_csv(path / "trades.csv", index=False)
        self.orders.to_csv(path / "orders.csv", index=False)
        self.order_events.to_csv(path / "order_events.csv", index=False)
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
        broker = BacktestBroker(self.config)
        broker.max_position_notional = self.risk_manager.config.max_position_notional
        equity_rows: list[dict[str, object]] = []
        session_key = None
        session_start_equity = self.config.initial_cash
        risk_halted = False

        timestamps = list(data["timestamp"].drop_duplicates())
        for index, timestamp in enumerate(timestamps):
            current_session_key = pd.Timestamp(timestamp).date()
            if current_session_key != session_key:
                session_key = current_session_key
                session_start_equity = broker.get_equity() if broker.latest_prices else self.config.initial_cash
                risk_halted = False

            current = data[data["timestamp"] == timestamp]
            broker.process_bar(pd.Timestamp(timestamp), index, current)

            equity_after_fills = broker.get_equity()
            daily_pnl = equity_after_fills - session_start_equity
            if daily_pnl <= -self.risk_manager.config.max_daily_loss:
                risk_halted = True

            if risk_halted or self.risk_manager.config.kill_switch:
                orders = broker.flatten_orders(pd.Timestamp(timestamp))
            else:
                history = data[data["timestamp"] <= timestamp]
                orders = self.strategy.generate_orders(history, pd.Timestamp(timestamp), broker)
            orders = self.risk_manager.validate_orders(orders, broker.latest_prices, pd.Timestamp(timestamp))
            for order in orders:
                broker.submit_order(order)

            equity = broker.get_equity()
            gross_exposure = broker.gross_exposure()
            equity_rows.append(
                {
                    "timestamp": timestamp,
                    "cash": broker.get_cash(),
                    "market_value": broker.get_market_value(),
                    "equity": equity,
                    "gross_exposure": gross_exposure,
                    "daily_pnl": daily_pnl,
                    "risk_halted": risk_halted,
                    "open_orders": broker.open_order_count(),
                }
            )

        equity_curve = pd.DataFrame(equity_rows)
        trades = broker.trade_log()
        metrics = calculate_performance_metrics(equity_curve, trades, self.config.annualization_periods)
        return BacktestResult(
            equity_curve=equity_curve,
            trades=trades,
            orders=broker.order_log(),
            order_events=broker.order_events(),
            metrics=metrics,
        )
