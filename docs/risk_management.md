# Risk Management

Risk controls are shared by backtests and paper-trading order planning.

Implemented controls:

- `max_gross_exposure`: caps total absolute target exposure.
- `max_symbol_exposure`: caps each symbol target fraction.
- `max_position_notional`: caps desired position notional.
- `max_order_notional`: caps a single order intent.
- `max_position_quantity`: caps order quantity.
- `max_daily_loss`: halts new entries in backtests and targets open positions flat.
- `allow_short`: clips short targets to flat when disabled.
- `trading_session_start` and `trading_session_end`: optional HH:MM session filter.
- `kill_switch`: blocks new orders and forces flat targets in backtests.

Risk checks happen before simulated fills or broker submission. These checks are simple guardrails, not a substitute for broker controls, monitoring, or human review.

Live trading remains disabled by default. Before any live use, require explicit live configuration, order confirmation, kill-switch validation, max daily loss validation, max position validation, max order notional validation, and an operational checklist.
