from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


def plot_strategy_diagnostics(
    bars: pd.DataFrame,
    trades: pd.DataFrame,
    output_path: str | Path,
    symbol: str | None = None,
    title: str | None = None,
    overlays: list[str] | None = None,
    oscillator_panels: list[str] | None = None,
) -> Path:
    """Plot price action, trades, and common diagnostics for one symbol."""
    if bars.empty:
        raise ValueError("bars must not be empty.")

    _ensure_matplotlib_cache()
    import matplotlib.pyplot as plt

    selected_symbol = (symbol or str(bars["symbol"].iloc[0])).upper()
    frame = _with_indicators(_symbol_frame(bars, selected_symbol))
    trade_frame = _symbol_frame(trades, selected_symbol) if not trades.empty and "symbol" in trades else pd.DataFrame()

    overlays = overlays or ["ma_5", "ma_20", "vwap", "bbands"]
    oscillator_panels = oscillator_panels or ["rsi", "macd", "volume"]
    panel_count = 1 + len(oscillator_panels)
    height_ratios = [3.0] + [1.0] * len(oscillator_panels)
    fig, axes = plt.subplots(panel_count, 1, figsize=(14, 3.2 * panel_count), sharex=True, gridspec_kw={"height_ratios": height_ratios})
    if panel_count == 1:
        axes = [axes]

    x = range(len(frame))
    _plot_candles(axes[0], frame, x)
    _plot_price_overlays(axes[0], frame, overlays)
    _plot_trade_markers(axes[0], frame, trade_frame)
    axes[0].set_title(title or f"{selected_symbol} Strategy Diagnostics")
    axes[0].set_ylabel("Price")
    axes[0].legend(loc="best")
    axes[0].grid(alpha=0.2)

    for axis, panel in zip(axes[1:], oscillator_panels):
        if panel == "rsi":
            _plot_rsi(axis, frame)
        elif panel == "macd":
            _plot_macd(axis, frame)
        elif panel == "volume":
            _plot_volume(axis, frame, x)
        else:
            _plot_custom_panel(axis, frame, panel)
        axis.grid(alpha=0.2)

    tick_step = max(len(frame) // 8, 1)
    ticks = list(range(0, len(frame), tick_step))
    axes[-1].set_xticks(ticks)
    axes[-1].set_xticklabels([str(frame["timestamp"].iloc[i]) for i in ticks], rotation=30, ha="right")
    axes[-1].set_xlabel("Timestamp")
    fig.tight_layout()

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_trade_window(
    bars: pd.DataFrame,
    trades: pd.DataFrame,
    trade_index: int,
    output_path: str | Path,
    window_bars: int = 20,
) -> Path:
    if trades.empty:
        raise ValueError("trades must not be empty.")
    if trade_index < 0 or trade_index >= len(trades):
        raise IndexError("trade_index is out of range.")

    trade = trades.iloc[trade_index]
    symbol = str(trade["symbol"]).upper()
    timestamp = pd.Timestamp(trade["timestamp"])
    frame = _symbol_frame(bars, symbol)
    center_candidates = frame.index[frame["timestamp"] >= timestamp]
    center = int(center_candidates[0]) if len(center_candidates) else len(frame) - 1
    start = max(center - window_bars, 0)
    end = min(center + window_bars + 1, len(frame))
    window = frame.iloc[start:end].reset_index(drop=True)
    window_trades = _symbol_frame(trades, symbol)
    window_trades = window_trades[
        (window_trades["timestamp"] >= window["timestamp"].min()) & (window_trades["timestamp"] <= window["timestamp"].max())
    ]
    return plot_strategy_diagnostics(
        window,
        window_trades,
        output_path=output_path,
        symbol=symbol,
        title=f"{symbol} Trade Window #{trade_index}",
    )


def _symbol_frame(data: pd.DataFrame, symbol: str) -> pd.DataFrame:
    frame = data.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame = frame[frame["symbol"] == symbol.upper()].copy()
    if "timestamp" in frame:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.sort_values("timestamp")
    return frame.reset_index(drop=True)


def _ensure_matplotlib_cache() -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(Path("/tmp/qts_matplotlib").resolve()))


def _with_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    close = result["close"]
    result["ma_5"] = close.rolling(5).mean()
    result["ma_20"] = close.rolling(20).mean()
    result["vwap_plot"] = result["vwap"] if "vwap" in result and result["vwap"].notna().any() else _rolling_vwap(result)
    rolling_20 = close.rolling(20)
    result["bb_mid"] = rolling_20.mean()
    result["bb_upper"] = result["bb_mid"] + 2 * rolling_20.std()
    result["bb_lower"] = result["bb_mid"] - 2 * rolling_20.std()
    result["rsi_14"] = _rsi(close)
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    result["macd"] = ema_12 - ema_26
    result["macd_signal"] = result["macd"].ewm(span=9, adjust=False).mean()
    result["macd_hist"] = result["macd"] - result["macd_signal"]
    return result


def _rolling_vwap(frame: pd.DataFrame, window: int = 20) -> pd.Series:
    typical = (frame["high"] + frame["low"] + frame["close"]) / 3
    volume = frame["volume"].replace(0, float("nan"))
    return (typical * volume).rolling(window).sum() / volume.rolling(window).sum()


def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0).rolling(window).mean()
    losses = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gains / losses.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((losses == 0) & (gains > 0), 100.0)
    rsi = rsi.mask((gains == 0) & (losses > 0), 0.0)
    rsi = rsi.mask((gains == 0) & (losses == 0), 50.0)
    return rsi.astype(float)


def _plot_candles(axis, frame: pd.DataFrame, x) -> None:
    from matplotlib.patches import Rectangle

    width = 0.6
    for idx, row in frame.iterrows():
        color = "#207567" if row["close"] >= row["open"] else "#a33b3b"
        axis.vlines(idx, row["low"], row["high"], color=color, linewidth=0.8, alpha=0.8)
        lower = min(row["open"], row["close"])
        height = abs(row["close"] - row["open"]) or 0.001
        axis.add_patch(Rectangle((idx - width / 2, lower), width, height, facecolor=color, edgecolor=color, alpha=0.75))


def _plot_price_overlays(axis, frame: pd.DataFrame, overlays: list[str]) -> None:
    if "ma_5" in overlays:
        axis.plot(frame.index, frame["ma_5"], label="MA 5", linewidth=1.2, color="#2f6db3")
    if "ma_20" in overlays:
        axis.plot(frame.index, frame["ma_20"], label="MA 20", linewidth=1.2, color="#9254a3")
    if "vwap" in overlays:
        axis.plot(frame.index, frame["vwap_plot"], label="VWAP", linewidth=1.1, color="#8a6f2a")
    if "bbands" in overlays:
        axis.plot(frame.index, frame["bb_upper"], label="BB Upper", linewidth=0.8, color="#777777", alpha=0.8)
        axis.plot(frame.index, frame["bb_lower"], label="BB Lower", linewidth=0.8, color="#777777", alpha=0.8)
        axis.fill_between(frame.index, frame["bb_lower"].astype(float), frame["bb_upper"].astype(float), color="#999999", alpha=0.08)


def _plot_trade_markers(axis, frame: pd.DataFrame, trades: pd.DataFrame) -> None:
    if trades.empty:
        return
    timestamp_to_x = {timestamp: idx for idx, timestamp in enumerate(frame["timestamp"])}
    for _, trade in trades.iterrows():
        trade_time = pd.Timestamp(trade["timestamp"])
        x = _nearest_x(frame, timestamp_to_x, trade_time)
        if x is None:
            continue
        price = float(trade.get("fill_price", frame["close"].iloc[x]))
        side = str(trade.get("side", "")).lower()
        if side == "buy":
            axis.scatter(x, price, marker="^", color="#1f9d55", s=70, label="Buy" if "Buy" not in axis.get_legend_handles_labels()[1] else None, zorder=5)
        elif side == "sell":
            axis.scatter(x, price, marker="v", color="#d13f3f", s=70, label="Sell" if "Sell" not in axis.get_legend_handles_labels()[1] else None, zorder=5)


def _nearest_x(frame: pd.DataFrame, timestamp_to_x: dict[pd.Timestamp, int], timestamp: pd.Timestamp) -> int | None:
    if timestamp in timestamp_to_x:
        return timestamp_to_x[timestamp]
    candidates = frame.index[frame["timestamp"] >= timestamp]
    if len(candidates):
        return int(candidates[0])
    return None


def _plot_rsi(axis, frame: pd.DataFrame) -> None:
    axis.plot(frame.index, frame["rsi_14"], label="RSI 14", color="#5b6f8f", linewidth=1.1)
    axis.axhline(70, color="#a33b3b", linestyle="--", linewidth=0.8)
    axis.axhline(30, color="#207567", linestyle="--", linewidth=0.8)
    axis.set_ylabel("RSI")
    axis.legend(loc="best")


def _plot_macd(axis, frame: pd.DataFrame) -> None:
    axis.plot(frame.index, frame["macd"], label="MACD", color="#2f6db3", linewidth=1.1)
    axis.plot(frame.index, frame["macd_signal"], label="Signal", color="#a8642a", linewidth=1.1)
    colors = ["#207567" if value >= 0 else "#a33b3b" for value in frame["macd_hist"].fillna(0)]
    axis.bar(frame.index, frame["macd_hist"], color=colors, alpha=0.35)
    axis.set_ylabel("MACD")
    axis.legend(loc="best")


def _plot_volume(axis, frame: pd.DataFrame, x) -> None:
    colors = ["#207567" if close >= open_ else "#a33b3b" for open_, close in zip(frame["open"], frame["close"])]
    axis.bar(x, frame["volume"], color=colors, alpha=0.45)
    axis.set_ylabel("Volume")


def _plot_custom_panel(axis, frame: pd.DataFrame, column: str) -> None:
    if column not in frame:
        axis.text(0.5, 0.5, f"Missing column: {column}", ha="center", va="center", transform=axis.transAxes)
        axis.set_ylabel(column)
        return
    axis.plot(frame.index, frame[column], label=column)
    axis.set_ylabel(column)
    axis.legend(loc="best")
