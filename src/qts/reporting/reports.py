from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from qts import __version__
from qts.backtest.engine import BacktestResult
from qts.config.models import AppConfig
from qts.reporting.charts import plot_strategy_diagnostics


def write_backtest_report(
    result: BacktestResult,
    output_dir: str | Path,
    make_chart: bool = True,
    metadata: dict[str, object] | None = None,
    market_data: pd.DataFrame | None = None,
    diagnostic_symbols: list[str] | None = None,
) -> None:
    result.write(output_dir)
    path = Path(output_dir)
    if metadata is not None:
        with (path / "run_metadata.json").open("w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2)
    if not make_chart or result.equity_curve.empty:
        return
    os.environ.setdefault("MPLCONFIGDIR", str(Path("/tmp/qts_matplotlib").resolve()))
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5))
    result.equity_curve.plot(x="timestamp", y="equity", ax=ax, legend=False)
    ax.set_title("Equity Curve")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Equity")
    fig.tight_layout()
    fig.savefig(path / "equity_curve.png")
    plt.close(fig)

    if market_data is not None and not market_data.empty:
        symbols = diagnostic_symbols or sorted(market_data["symbol"].astype(str).str.upper().unique().tolist())
        for symbol in symbols:
            plot_strategy_diagnostics(
                bars=market_data,
                trades=result.trades,
                output_path=path / f"{symbol}_diagnostics.png",
                symbol=symbol,
            )


def build_run_metadata(config: AppConfig, data: pd.DataFrame, run_type: str) -> dict[str, object]:
    data_summary: dict[str, object] = {
        "rows": int(len(data)),
        "symbols": sorted(data["symbol"].unique().tolist()) if "symbol" in data else [],
        "start": str(data["timestamp"].min()) if "timestamp" in data and not data.empty else None,
        "end": str(data["timestamp"].max()) if "timestamp" in data and not data.empty else None,
        "source": config.data.source,
        "timeframe": config.data.timeframe,
    }
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "qts_version": __version__,
        "run_type": run_type,
        "config": config.model_dump(mode="json"),
        "data": data_summary,
    }
