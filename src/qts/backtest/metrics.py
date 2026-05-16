from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_performance_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    annualization_periods: int = 252,
) -> dict[str, float]:
    if equity_curve.empty:
        return {}
    equity = equity_curve["equity"].astype(float)
    returns = equity.pct_change().fillna(0.0)
    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0 if equity.iloc[0] else 0.0
    periods = max(len(returns), 1)
    annualized_return = (1.0 + total_return) ** (annualization_periods / periods) - 1.0
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    sharpe = np.sqrt(annualization_periods) * returns.mean() / returns.std(ddof=0) if returns.std(ddof=0) else 0.0

    closed = trades[trades["realized_pnl"].notna()].copy() if not trades.empty else pd.DataFrame()
    wins = closed[closed["realized_pnl"] > 0] if not closed.empty else pd.DataFrame()
    losses = closed[closed["realized_pnl"] < 0] if not closed.empty else pd.DataFrame()
    gross_profit = wins["realized_pnl"].sum() if not wins.empty else 0.0
    gross_loss = abs(losses["realized_pnl"].sum()) if not losses.empty else 0.0
    exposure_time = float((equity_curve["gross_exposure"] > 0).mean()) if "gross_exposure" in equity_curve else 0.0
    holding = closed["holding_period_bars"].dropna() if "holding_period_bars" in closed else pd.Series(dtype=float)

    return {
        "total_return": float(total_return),
        "annualized_return": float(annualized_return),
        "max_drawdown": float(drawdown.min()),
        "sharpe_ratio": float(sharpe),
        "win_rate": float(len(wins) / len(closed)) if len(closed) else 0.0,
        "profit_factor": float(gross_profit / gross_loss) if gross_loss else float("inf") if gross_profit else 0.0,
        "average_trade_return": float(closed["trade_return"].mean()) if "trade_return" in closed and len(closed) else 0.0,
        "number_of_trades": float(len(closed)),
        "exposure_time": exposure_time,
        "average_holding_period": float(holding.mean()) if len(holding) else 0.0,
    }

