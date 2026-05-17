import pandas as pd

from qts.data.validation import normalize_market_data
from qts.ml.signal_provider import MLSignalProvider
from qts.signals.base import SignalDirection, SignalType, TradingSignal
from qts.signals.combiners import WeightedSignalCombiner
from qts.signals.rule_based import BreakoutSignal, MovingAverageCrossoverSignal


def test_moving_average_signal_emits_standard_signal() -> None:
    rows = []
    closes = [100.0] * 10 + [110.0]
    for i, close in enumerate(closes):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-01T14:30:00Z") + pd.Timedelta(minutes=i),
                "symbol": "SPY",
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1000,
            }
        )
    data = normalize_market_data(pd.DataFrame(rows))
    provider = MovingAverageCrossoverSignal(fast_window=3, slow_window=10)
    signals = provider.generate(data, data["timestamp"].iloc[-1])
    assert len(signals) == 1
    assert signals[0].direction == SignalDirection.LONG
    assert signals[0].target_position == 1.0
    assert signals[0].provenance is not None
    assert signals[0].provenance.source_name == "moving_average_crossover"
    assert signals[0].provenance.source_type == SignalType.RULE_BASED
    assert "ma_3" in signals[0].provenance.feature_set
    assert signals[0].confidence_metadata["method"] == "deterministic_rule"


def test_ml_signal_provider_validates_threshold_order() -> None:
    class DummyModel:
        feature_columns = []

    try:
        MLSignalProvider(DummyModel(), long_threshold=0.4, short_threshold=0.6)
    except ValueError as exc:
        assert "Thresholds" in str(exc)
    else:
        raise AssertionError("Expected invalid threshold order to raise ValueError.")


def test_breakout_signal_uses_prior_window() -> None:
    rows = []
    closes = [100, 101, 102, 103, 104, 110]
    for i, close in enumerate(closes):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-01T14:30:00Z") + pd.Timedelta(minutes=i),
                "symbol": "SPY",
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 1000,
            }
        )
    data = normalize_market_data(pd.DataFrame(rows))
    signals = BreakoutSignal(window=3).generate(data, data["timestamp"].iloc[-1])

    assert signals[0].direction == SignalDirection.LONG
    assert signals[0].provenance is not None
    assert "prior_high_3" in signals[0].provenance.feature_set


def test_weighted_signal_combiner_handles_conflicts_as_flat() -> None:
    timestamp = pd.Timestamp("2024-01-01T14:30:00Z").to_pydatetime()
    signals = [
        TradingSignal(timestamp, "SPY", SignalType.RULE_BASED, SignalDirection.LONG, strength=1.0, confidence=1.0, metadata={"provider": "a"}),
        TradingSignal(timestamp, "SPY", SignalType.ML, SignalDirection.SHORT, strength=1.0, confidence=1.0, metadata={"provider": "b"}),
    ]

    combined = WeightedSignalCombiner(method="equal_weight").combine(signals)

    assert len(combined) == 1
    assert combined[0].direction == SignalDirection.FLAT
    assert combined[0].target_position == 0.0
    assert combined[0].metadata["conflict"] is True
