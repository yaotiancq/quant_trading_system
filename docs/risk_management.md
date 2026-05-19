# Risk Management

Risk controls are shared by backtests and paper-trading order planning. The risk manager sits between strategy output and broker submission:

```text
Strategy -> OrderRequest -> RiskManager -> BrokerAdapter
```

Implemented controls:

- `max_gross_exposure` / `max_portfolio_exposure`: caps total absolute exposure.
- `max_symbol_exposure`: caps each symbol target fraction.
- `max_position_notional`: caps desired position notional.
- `max_order_notional`: caps a single order intent.
- `max_position_quantity` / `max_position_qty`: caps order quantity.
- `max_daily_loss`: halts new entries in backtests and targets open positions flat.
- `allow_short`: clips short targets to flat when disabled.
- `trading_session_start` and `trading_session_end`: optional HH:MM session filter.
- `kill_switch`: blocks new orders and forces flat targets in backtests.

Risk checks happen before simulated fills or broker submission. In backtests, `BacktestEngine` calls `RiskManager.validate_orders` before `BacktestBroker.submit_order`. In paper/live modes, the same order validation should happen before `AlpacaPaperBroker` or `AlpacaLiveBroker` submission.

The risk layer receives current effective position quantities so order sides remain strict:

- `SELL` can reduce or close a long position, but cannot open a short.
- `SELL_SHORT` is required for opening or increasing a short position.
- `BUY_TO_COVER` can reduce or close a short position, but cannot open a long.
- `BUY` is required for opening or increasing a long position.

Risk liquidation orders use `validate_liquidation_orders`. These orders still pass order-type validation, but bypass normal max-order-notional and max-quantity limits so max-loss and kill-switch exits can flatten the complete position.

These checks are simple guardrails, not a substitute for broker controls, monitoring, or human review.

Live trading remains disabled by default. Before any live use, require explicit live configuration, order confirmation, kill-switch validation, max daily loss validation, max position validation, max order notional validation, and an operational checklist.
