from __future__ import annotations

import time
from dataclasses import dataclass

from qts.config.loader import EnvSettings
from qts.config.models import AppConfig
from qts.execution.alpaca_broker import AlpacaBrokerAdapter
from qts.utils.logging import get_logger


@dataclass(frozen=True)
class PaperLoopResult:
    status: str
    iterations: int
    dry_run: bool


def run_paper_loop(
    config: AppConfig,
    settings: EnvSettings,
    dry_run: bool | None = None,
    connect: bool = False,
    iterations: int | None = None,
) -> PaperLoopResult:
    logger = get_logger(__name__)
    effective_dry_run = config.execution.dry_run if dry_run is None else dry_run
    if not config.execution.paper and not config.execution.live_trading_enabled:
        raise ValueError("Live trading is disabled by default and requires live_trading_enabled=true.")
    if config.execution.live_trading_enabled and not config.execution.order_confirmation_required:
        raise ValueError("Live trading requires order_confirmation_required=true.")

    if effective_dry_run and not connect:
        logger.info("Dry-run validation complete. No Alpaca connection was opened and no orders were submitted.")
        return PaperLoopResult(status="dry_run_validated", iterations=0, dry_run=True)

    if not settings.has_alpaca_credentials:
        raise ValueError("Alpaca API credentials are required for paper trading connectivity.")

    broker = AlpacaBrokerAdapter(
        settings,
        paper=config.execution.paper,
        live_trading_enabled=config.execution.live_trading_enabled,
    )
    max_iterations = iterations if iterations is not None else 1 if effective_dry_run else None
    count = 0
    while True:
        clock = broker.get_clock()
        account = broker.get_account()
        positions = broker.get_positions()
        count += 1
        logger.info(
            "Clock=%s equity=%s buying_power=%s positions=%s dry_run=%s",
            clock,
            getattr(account, "equity", None),
            getattr(account, "buying_power", None),
            len(positions),
            effective_dry_run,
        )
        if max_iterations is not None and count >= max_iterations:
            break
        time.sleep(config.execution.poll_interval_seconds)

    return PaperLoopResult(status="completed", iterations=count, dry_run=effective_dry_run)


__all__ = ["PaperLoopResult", "run_paper_loop"]
