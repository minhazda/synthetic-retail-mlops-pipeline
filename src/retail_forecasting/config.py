"""Typed, YAML-driven configuration.

No values are hard-coded in business logic — everything flows from
``configs/config.yaml`` (overridable via the ``RF_CONFIG`` environment
variable). Paths are resolved relative to the config file's directory so the
same config works on a laptop, in Docker, and in CI.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .exceptions import ConfigError

DEFAULT_CONFIG_ENV = "RF_CONFIG"
DEFAULT_CONFIG_PATH = "configs/config.yaml"


@dataclass(frozen=True)
class DataConfig:
    """Paths and identifiers for raw and processed datasets."""

    raw_path: Path
    processed_path: Path
    target_column: str = "sales_volume"
    timestamp_column: str = "timestamp"
    id_column: str = "product_id"


@dataclass(frozen=True)
class GeneratorConfig:
    """Parameters for the reproducible synthetic data generator."""

    num_days: int = 60
    num_products: int = 100
    seed: int = 42
    start_date: str = "2025-01-01"


@dataclass(frozen=True)
class TrainConfig:
    """Hyperparameters and split settings for model training."""

    test_size: float = 0.2
    model_dir: Path = Path("models")
    model_filename: str = "lgbm_model.joblib"
    random_state: int = 42
    lgbm_params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MLflowConfig:
    """Experiment tracking settings."""

    tracking_uri: str = "file:./mlruns"
    experiment_name: str = "retail-demand-forecasting"
    registered_model_name: str = "retail-lgbm"


@dataclass(frozen=True)
class Config:
    """Top-level application configuration."""

    data: DataConfig
    generator: GeneratorConfig
    train: TrainConfig
    mlflow: MLflowConfig
    log_level: str = "INFO"


def _resolve(base: Path, value: str) -> Path:
    """Resolve ``value`` against ``base`` unless it is already absolute."""
    p = Path(value)
    return p if p.is_absolute() else (base / p).resolve()


def load_config(path: str | os.PathLike[str] | None = None) -> Config:
    """Load and validate configuration from a YAML file.

    Args:
        path: Explicit config path. Falls back to ``$RF_CONFIG`` then to
            ``configs/config.yaml`` relative to the current working directory.

    Returns:
        A fully populated, immutable :class:`Config`.

    Raises:
        ConfigError: If the file is missing or any required section is absent.
    """
    cfg_path = Path(path or os.environ.get(DEFAULT_CONFIG_ENV, DEFAULT_CONFIG_PATH))
    if not cfg_path.is_file():
        raise ConfigError(f"Config file not found: {cfg_path}")

    try:
        raw: dict[str, Any] = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise ConfigError(f"Invalid YAML in {cfg_path}: {exc}") from exc

    base = cfg_path.parent
    try:
        data_raw = raw["data"]
        data = DataConfig(
            raw_path=_resolve(base, data_raw["raw_path"]),
            processed_path=_resolve(base, data_raw["processed_path"]),
            target_column=data_raw.get("target_column", "sales_volume"),
            timestamp_column=data_raw.get("timestamp_column", "timestamp"),
            id_column=data_raw.get("id_column", "product_id"),
        )
        gen_raw = raw.get("generator", {})
        generator = GeneratorConfig(**gen_raw)
        train_raw = dict(raw.get("train", {}))
        if "model_dir" in train_raw:
            train_raw["model_dir"] = _resolve(base, train_raw["model_dir"])
        train = TrainConfig(**train_raw)
        mlflow_cfg = MLflowConfig(**raw.get("mlflow", {}))
    except (KeyError, TypeError) as exc:
        raise ConfigError(f"Malformed config section: {exc}") from exc

    return Config(
        data=data,
        generator=generator,
        train=train,
        mlflow=mlflow_cfg,
        log_level=raw.get("log_level", "INFO"),
    )
