from __future__ import annotations


def apply_slippage(price: float, signed_quantity: float, slippage_bps: float) -> float:
    direction = 1 if signed_quantity > 0 else -1
    return price * (1 + direction * slippage_bps / 10_000)


def per_share_commission(quantity: float, commission_per_share: float) -> float:
    return abs(quantity) * commission_per_share


__all__ = ["apply_slippage", "per_share_commission"]
