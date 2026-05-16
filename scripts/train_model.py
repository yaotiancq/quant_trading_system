from __future__ import annotations

import argparse

from qts.config.loader import load_app_config
from qts.data.loader import load_market_data
from qts.ml.dataset import build_supervised_dataset, time_train_test_split
from qts.ml.model import BaselineModel
from qts.utils.logging import configure_logging, get_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a baseline logistic regression signal model.")
    parser.add_argument("--config", default="configs/backtest.yaml")
    parser.add_argument("--output", default="models/baseline_logistic.joblib")
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--threshold", type=float, default=0.0)
    parser.add_argument("--train-fraction", type=float, default=0.7)
    args = parser.parse_args()

    configure_logging()
    logger = get_logger(__name__)
    config = load_app_config(args.config)
    bars = load_market_data(config.data)
    X, y, feature_columns, metadata = build_supervised_dataset(bars, horizon=args.horizon, threshold=args.threshold)
    X_train, X_test, y_train, y_test, _, _ = time_train_test_split(X, y, metadata, train_fraction=args.train_fraction)
    model = BaselineModel(feature_columns).fit(X_train, y_train)
    output = model.save(args.output)
    logger.info("Saved model to %s", output)
    logger.info("Train accuracy: %.4f", model.score(X_train, y_train))
    logger.info("Test accuracy: %.4f", model.score(X_test, y_test) if len(X_test) else 0.0)


if __name__ == "__main__":
    main()

