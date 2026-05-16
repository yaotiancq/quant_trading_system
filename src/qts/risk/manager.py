from __future__ import annotations

from qts.config.models import RiskConfig
from qts.strategies.base import TargetPosition


class RiskManager:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def validate_targets(self, targets: list[TargetPosition]) -> list[TargetPosition]:
        if self.config.kill_switch:
            return []
        approved: list[TargetPosition] = []
        gross = 0.0
        for target in targets:
            if target.target_fraction < 0 and not self.config.allow_short:
                clipped = 0.0
            else:
                clipped = max(min(target.target_fraction, self.config.max_symbol_exposure), -self.config.max_symbol_exposure)
            gross += abs(clipped)
            approved.append(
                TargetPosition(
                    timestamp=target.timestamp,
                    symbol=target.symbol,
                    target_fraction=clipped,
                    metadata=target.metadata,
                )
            )
        if gross <= self.config.max_gross_exposure:
            return approved
        scale = self.config.max_gross_exposure / gross if gross else 0.0
        return [
            TargetPosition(t.timestamp, t.symbol, t.target_fraction * scale, t.metadata)
            for t in approved
        ]

