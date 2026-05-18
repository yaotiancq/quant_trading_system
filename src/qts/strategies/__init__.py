from qts.strategies.base import OrderRequest, Strategy, TargetPosition

__all__ = ["OrderRequest", "SignalDrivenStrategy", "Strategy", "TargetPosition", "create_strategy_from_config"]


def __getattr__(name: str) -> object:
    if name in {"SignalDrivenStrategy", "create_strategy_from_config"}:
        from qts.strategies.signal_strategy import SignalDrivenStrategy, create_strategy_from_config

        return {
            "SignalDrivenStrategy": SignalDrivenStrategy,
            "create_strategy_from_config": create_strategy_from_config,
        }[name]
    raise AttributeError(name)
