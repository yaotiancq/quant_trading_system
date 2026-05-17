from __future__ import annotations

import pandas as pd

from qts.features.technical import calculate_rsi
from qts.signals.base import SignalDirection, SignalProvenance, SignalType, TradingSignal


class MovingAverageCrossoverSignal:
    name = "moving_average_crossover"

    def __init__(
        self,
        fast_window: int = 5,
        slow_window: int = 20,
        target_notional_fraction: float = 1.0,
        min_spread: float = 0.0,
    ) -> None:
        if fast_window >= slow_window:
            raise ValueError("fast_window must be smaller than slow_window.")

        self.fast_window = fast_window
        self.slow_window = slow_window
        self.target_notional_fraction = target_notional_fraction
        self.min_spread = min_spread

    def generate(self, history: pd.DataFrame, timestamp: pd.Timestamp) -> list[TradingSignal]:
        signals: list[TradingSignal] = []

        # If signal is generated after bar close, <= timestamp is acceptable.
        # If signal is generated before bar close, use < timestamp instead.
        available = history[history["timestamp"] <= timestamp]

        for symbol, frame in available.groupby("symbol", sort=False):
            frame = frame.sort_values("timestamp")

            # Need one extra bar to compare previous MA state with current MA state
            if len(frame) < self.slow_window + 1:
                signals.append(_hold(timestamp, symbol, self.name, reason="insufficient_history"))
                continue

            closes = pd.to_numeric(frame["close"], errors="coerce").dropna()

            if len(closes) < self.slow_window + 1:
                signals.append(_hold(timestamp, symbol, self.name, reason="insufficient_history"))
                continue

            curr_fast = closes.tail(self.fast_window).mean()
            curr_slow = closes.tail(self.slow_window).mean()

            prev_closes = closes.iloc[:-1]
            #prev_closes = closes.iloc[:]
            prev_fast = prev_closes.tail(self.fast_window).mean()
            prev_slow = prev_closes.tail(self.slow_window).mean()

            if curr_slow == 0 or prev_slow == 0:
                signals.append(_hold(timestamp, symbol, self.name, reason="invalid_moving_average"))
                continue

            curr_spread = (curr_fast - curr_slow) / curr_slow
            prev_spread = (prev_fast - prev_slow) / prev_slow

            crossed_up = prev_spread <= 0 and curr_spread > self.min_spread
            crossed_down = prev_spread >= 0 and curr_spread < -self.min_spread

            if crossed_up:
                direction = SignalDirection.LONG
            elif crossed_down:
                direction = SignalDirection.SHORT
            else:
                signals.append(_hold(timestamp, symbol, self.name, reason="no_crossover"))
                continue

            target_position = (
                self.target_notional_fraction
                if direction == SignalDirection.LONG
                else -self.target_notional_fraction
            )

            signals.append(
                TradingSignal(
                    timestamp=timestamp.to_pydatetime(),
                    symbol=symbol,
                    signal_type=SignalType.RULE_BASED,
                    direction=direction,
                    strength=min(abs(curr_spread) * 100.0, 1.0),
                    confidence=1.0,
                    target_position=target_position,
                    provenance=SignalProvenance(
                        source_name=self.name,
                        source_type=SignalType.RULE_BASED,
                        feature_set=(
                            f"ma_{self.fast_window}",
                            f"ma_{self.slow_window}",
                            "close",
                        ),
                    ),
                    confidence_metadata={
                        "method": "deterministic_rule",
                        "confidence_basis": "ma_crossover",
                    },
                    metadata={
                        "provider": self.name,
                        "curr_fast": float(curr_fast),
                        "curr_slow": float(curr_slow),
                        "prev_fast": float(prev_fast),
                        "prev_slow": float(prev_slow),
                        "curr_spread": float(curr_spread),
                        "prev_spread": float(prev_spread),
                        "crossed_up": crossed_up,
                        "crossed_down": crossed_down,
                        "min_spread": self.min_spread,
                    },
                )
            )

        return signals


class RsiMeanReversionSignal:
    name = "rsi_mean_reversion"

    def __init__(self, window: int = 14, lower: float = 30.0, upper: float = 70.0, target_notional_fraction: float = 1.0) -> None:
        self.window = window
        self.lower = lower
        self.upper = upper
        self.target_notional_fraction = target_notional_fraction

    def generate(self, history: pd.DataFrame, timestamp: pd.Timestamp) -> list[TradingSignal]:
        signals: list[TradingSignal] = []
        available = history[history["timestamp"] <= timestamp]
        for symbol, frame in available.groupby("symbol", sort=False):
            closes = frame.sort_values("timestamp")["close"]
            if len(closes) < self.window + 1:
                signals.append(_hold(timestamp, symbol, self.name, reason="insufficient_history"))
                continue
            rsi = calculate_rsi(closes, self.window).iloc[-1]
            if pd.isna(rsi):
                signals.append(_hold(timestamp, symbol, self.name, reason="insufficient_history"))
                continue
            direction = SignalDirection.LONG if rsi < self.lower else SignalDirection.SHORT if rsi > self.upper else SignalDirection.FLAT
            signals.append(
                TradingSignal(
                    timestamp=timestamp.to_pydatetime(),
                    symbol=symbol,
                    signal_type=SignalType.RULE_BASED,
                    direction=direction,
                    strength=min(abs(50.0 - rsi) / 50.0, 1.0),
                    confidence=1.0,
                    target_position=self.target_notional_fraction * (1 if direction == SignalDirection.LONG else -1 if direction == SignalDirection.SHORT else 0),
                    provenance=SignalProvenance(
                        source_name=self.name,
                        source_type=SignalType.RULE_BASED,
                        feature_set=(f"rsi_{self.window}", "close"),
                    ),
                    confidence_metadata={"method": "deterministic_rule", "confidence_basis": "rule_trigger"},
                    metadata={"provider": self.name, "rsi": float(rsi)},
                )
            )
        return signals


class BreakoutSignal:
    name = "breakout"

    def __init__(
        self,
        window: int = 20,
        target_notional_fraction: float = 1.0,
        breakout_buffer: float = 0.0,
    ) -> None:
        if window < 2:
            raise ValueError("window must be at least 2.")
        if not 0.0 <= target_notional_fraction <= 1.0:
            raise ValueError("target_notional_fraction must be between 0 and 1.")
        self.window = window
        self.target_notional_fraction = target_notional_fraction
        self.breakout_buffer = breakout_buffer

    def generate(self, history: pd.DataFrame, timestamp: pd.Timestamp) -> list[TradingSignal]:
        signals: list[TradingSignal] = []
        available = history[history["timestamp"] <= timestamp]
        for symbol, frame in available.groupby("symbol", sort=False):
            frame = frame.sort_values("timestamp")
            if len(frame) < self.window + 1:
                signals.append(_hold(timestamp, symbol, self.name, reason="insufficient_history"))
                continue

            prior_high = frame["high"].shift(1).rolling(self.window).max().iloc[-1]
            prior_low = frame["low"].shift(1).rolling(self.window).min().iloc[-1]
            close = float(frame["close"].iloc[-1])
            if pd.isna(prior_high) or pd.isna(prior_low) or prior_high <= 0 or prior_low <= 0:
                signals.append(_hold(timestamp, symbol, self.name, reason="insufficient_history"))
                continue

            upper_trigger = float(prior_high) * (1 + self.breakout_buffer)
            lower_trigger = float(prior_low) * (1 - self.breakout_buffer)
            if close > upper_trigger:
                direction = SignalDirection.LONG
                distance = close / upper_trigger - 1.0
            elif close < lower_trigger:
                direction = SignalDirection.SHORT
                distance = lower_trigger / close - 1.0
            else:
                direction = SignalDirection.FLAT
                distance = 0.0

            signed_target = 1 if direction == SignalDirection.LONG else -1 if direction == SignalDirection.SHORT else 0
            signals.append(
                TradingSignal(
                    timestamp=timestamp.to_pydatetime(),
                    symbol=symbol,
                    signal_type=SignalType.RULE_BASED,
                    direction=direction,
                    strength=min(abs(distance) * 100.0, 1.0),
                    confidence=1.0,
                    target_position=signed_target * self.target_notional_fraction,
                    provenance=SignalProvenance(
                        source_name=self.name,
                        source_type=SignalType.RULE_BASED,
                        feature_set=(f"prior_high_{self.window}", f"prior_low_{self.window}", "close"),
                    ),
                    confidence_metadata={"method": "deterministic_rule", "confidence_basis": "breakout"},
                    metadata={
                        "provider": self.name,
                        "prior_high": float(prior_high),
                        "prior_low": float(prior_low),
                        "close": close,
                        "breakout_buffer": self.breakout_buffer,
                    },
                )
            )
        return signals


def _hold(timestamp: pd.Timestamp, symbol: str, provider: str, reason: str = "hold") -> TradingSignal:
    return TradingSignal(
        timestamp=timestamp.to_pydatetime(),
        symbol=symbol,
        signal_type=SignalType.RULE_BASED,
        direction=SignalDirection.HOLD,
        provenance=SignalProvenance(source_name=provider, source_type=SignalType.RULE_BASED),
        confidence_metadata={"method": "deterministic_rule", "confidence_basis": reason},
        metadata={"provider": provider, "reason": reason},
    )
