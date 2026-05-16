import pandas as pd

from qts.data.validation import normalize_market_data
from qts.ml.signal_provider import MLSignalProvider
from qts.signals.base import SignalDirection, SignalType
from qts.signals.rule_based import MovingAverageCrossoverSignal


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
