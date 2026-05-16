# ML Integration

The ML layer is optional and first-class. Models do not place trades directly. They create standardized signals through `MLSignalProvider`.

## Workflow

1. Load historical bars.
2. Build deterministic features with `qts.features`.
3. Label examples using future returns.
4. Split train and test data by time.
5. Train the baseline logistic regression model.
6. Save the model with `joblib`.
7. Load the model for inference.
8. Convert probabilities into `TradingSignal` objects.
9. Backtest the ML signal provider through the same strategy and backtest engine used by rule-based signals.

ML `TradingSignal` objects include `SignalProvenance` with `source_type=ML`, `source_name`, `model_version`, and the feature set used for inference. Confidence metadata includes the predicted probability and decision thresholds.

## Bias Controls

- Feature functions use rolling and lagged market data only.
- Labels are shifted future returns and are not included in features.
- Splits are time-based, not random.
- Strategy and backtest code receive only history through the current timestamp.

The initial model is intentionally simple. XGBoost, LightGBM, PyTorch, online learning, and reinforcement learning policies can be added behind the same signal interface.
