"""Training pipeline: raw/processed data -> LightGBM model + MLflow run.

Reconciles the project onto a single canonical pipeline (LightGBM on hourly,
per-SKU data), matching the dissertation's headline result. The trained model
plus its feature schema are persisted with ``joblib`` and logged to MLflow's
experiment tracker and model registry.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .config import Config, load_config
from .data.generate import generate
from .exceptions import DataValidationError
from .features import build_features, feature_columns
from .logging_config import configure_logging, get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class TrainResult:
    """Outcome of a training run."""

    model_path: Path
    metrics: dict[str, float]
    feature_names: list[str]


def _load_or_build_dataset(cfg: Config) -> pd.DataFrame:
    """Load the processed dataset, deriving it from raw/synthetic if absent."""
    if cfg.data.processed_path.is_file():
        log.info("loading_processed", path=str(cfg.data.processed_path))
        raw = pd.read_csv(cfg.data.processed_path, parse_dates=[cfg.data.timestamp_column])
        # Already-processed files (legacy) are passed through untouched.
        if "sales_lag_1h" in raw.columns:
            return raw
        return build_features(raw)
    if cfg.data.raw_path.is_file():
        log.info("loading_raw", path=str(cfg.data.raw_path))
        raw = pd.read_csv(cfg.data.raw_path, parse_dates=[cfg.data.timestamp_column])
    else:
        log.info("no_data_found_generating_synthetic")
        raw = generate(cfg.generator)
    return build_features(raw)


def _evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Compute MAE, RMSE and MAPE (MAPE clipped to avoid divide-by-zero)."""
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mape = float(np.mean(np.abs((y_true - y_pred) / np.clip(y_true, 1, None))) * 100)
    return {"mae": mae, "rmse": rmse, "mape": mape}


def train(cfg: Config) -> TrainResult:
    """Train LightGBM with a time-ordered split and log to MLflow.

    Returns:
        :class:`TrainResult` with the artifact path, metrics, and feature names.

    Raises:
        DataValidationError: If the dataset has too few rows to split.
    """
    df = _load_or_build_dataset(cfg)
    df = df.sort_values(cfg.data.timestamp_column).reset_index(drop=True)

    if len(df) < 100:
        raise DataValidationError(f"Insufficient rows for training: {len(df)}")

    features = feature_columns(df)
    x = df[features]
    y = df[cfg.data.target_column]

    split_ix = int((1.0 - cfg.train.test_size) * len(df))
    x_train, x_test = x.iloc[:split_ix], x.iloc[split_ix:]
    y_train, y_test = y.iloc[:split_ix], y.iloc[split_ix:]

    mlflow.set_tracking_uri(cfg.mlflow.tracking_uri)
    mlflow.set_experiment(cfg.mlflow.experiment_name)

    with mlflow.start_run() as run:
        params = dict(cfg.train.lgbm_params)
        params.setdefault("random_state", cfg.train.random_state)
        model = LGBMRegressor(**params)
        model.fit(x_train, y_train)

        preds = model.predict(x_test)
        metrics = _evaluate(y_test.to_numpy(), np.asarray(preds))

        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.log_param("n_features", len(features))
        mlflow.log_param("n_train", len(x_train))
        try:
            mlflow.sklearn.log_model(
                model,
                artifact_path="model",
                registered_model_name=cfg.mlflow.registered_model_name,
            )
        except Exception as exc:  # registry may be unavailable in CI/local file store
            log.warning("model_registry_skipped", error=str(exc))

        log.info("training_complete", run_id=run.info.run_id, **metrics)

    # Persist a portable artifact (model + feature schema) for the API.
    cfg.train.model_dir.mkdir(parents=True, exist_ok=True)
    model_path = cfg.train.model_dir / cfg.train.model_filename
    joblib.dump({"model": model, "features": features}, model_path)
    log.info("model_persisted", path=str(model_path))

    return TrainResult(model_path=model_path, metrics=metrics, feature_names=features)


def main() -> None:
    """CLI entrypoint for the training service."""
    parser = argparse.ArgumentParser(description="Train the retail forecasting model.")
    parser.add_argument("--config", default=None, help="Path to config YAML.")
    args = parser.parse_args()

    cfg = load_config(args.config)
    configure_logging(cfg.log_level)
    result = train(cfg)
    log.info("done", model=str(result.model_path), **result.metrics)


if __name__ == "__main__":
    main()
