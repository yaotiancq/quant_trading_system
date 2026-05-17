from __future__ import annotations

import pandas as pd

from qts.data.validation import normalize_market_data
from qts.features.technical import add_basic_features, build_feature_matrix


def _bars() -> pd.DataFrame:
    rows = []
    for index in range(35):
        close = 100 + index * 0.5
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-02T14:30:00Z") + pd.Timedelta(minutes=index),
                "symbol": "SPY",
                "open": close - 0.1,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 10_000 + index * 10,
                "vwap": close - 0.05,
            }
        )
    return normalize_market_data(pd.DataFrame(rows))


def test_basic_features_include_ml_ready_columns() -> None:
    featured = add_basic_features(_bars())

    for column in ["log_return_1", "rsi_14", "vwap_deviation", "volume_ratio_5_20", "momentum_10"]:
        assert column in featured.columns
    assert featured["rsi_14"].dropna().between(0, 100).all()


def test_feature_matrix_drops_warmup_rows_without_lookahead() -> None:
    bars = _bars()
    matrix, columns = build_feature_matrix(bars)
    first_snapshot = matrix.iloc[0].copy()

    changed = bars.copy()
    changed.loc[changed.index[-1], "close"] = 10_000
    changed_matrix, _ = build_feature_matrix(changed, columns)

    assert not matrix.empty
    assert first_snapshot["timestamp"] == changed_matrix.iloc[0]["timestamp"]
    assert first_snapshot[columns].equals(changed_matrix.iloc[0][columns])
