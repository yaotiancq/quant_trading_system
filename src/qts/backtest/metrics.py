from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_performance_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    annualization_periods: int = 252,
    infer_periods: bool = True,
) -> dict[str, float]:
    if equity_curve.empty:
        return {}
    equity = equity_curve["equity"].astype(float)
    returns = equity.pct_change().fillna(0.0)
    annualization_periods_used = _annualization_periods(equity_curve, annualization_periods) if infer_periods else annualization_periods
    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0 if equity.iloc[0] else 0.0
    periods = max(len(returns), 1)
    annualized_return = _annualized_return(total_return, annualization_periods_used, periods)
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    sharpe = np.sqrt(annualization_periods_used) * returns.mean() / returns.std(ddof=0) if returns.std(ddof=0) else 0.0

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
        "annualization_periods_used": float(annualization_periods_used),
    }


def _annualization_periods(equity_curve: pd.DataFrame, fallback: int) -> int:
    if "timestamp" not in equity_curve or len(equity_curve) < 2:
        return fallback
    timestamps = pd.to_datetime(equity_curve["timestamp"], utc=True, errors="coerce").dropna().sort_values()
    if len(timestamps) < 2:
        return fallback
    deltas = timestamps.diff().dropna().dt.total_seconds()
    if deltas.empty:
        return fallback
    median_seconds = float(deltas.median())
    if median_seconds <= 0:
        return fallback
    if median_seconds < 23 * 60 * 60:
        trading_seconds_per_year = 252 * 6.5 * 60 * 60
        return max(int(round(trading_seconds_per_year / median_seconds)), 1)
    return fallback


def _annualized_return(total_return: float, annualization_periods: int, periods: int) -> float:
    if total_return <= -1.0:
        return -1.0
    log_return = np.log1p(total_return) * (annualization_periods / max(periods, 1))
    if log_return > 709:
        return float("inf")
    if log_return < -745:
        return -1.0
    return float(np.expm1(log_return))
