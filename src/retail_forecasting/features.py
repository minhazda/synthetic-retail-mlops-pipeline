"""Single, shared feature-engineering pipeline.

This module is the **one** place where raw hourly data is turned into the
modelling matrix — used identically by training, batch scoring, and the
inference API, eliminating training/serving skew.

Raw schema (per row): timestamp, product_id, category, sales_volume,
stock_level, promo_flag, holiday_flag, weather, foot_traffic.
"""

from __future__ import annotations

import pandas as pd

from .exceptions import DataValidationError

RAW_REQUIRED_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "product_id",
    "category",
    "sales_volume",
    "stock_level",
    "promo_flag",
    "holiday_flag",
    "weather",
    "foot_traffic",
)

# Columns that are never used as model inputs.
NON_FEATURE_COLUMNS: tuple[str, ...] = ("timestamp", "product_id", "sales_volume")


def validate_raw(df: pd.DataFrame) -> None:
    """Validate that a raw frame has the required columns and no nulls there.

    Raises:
        DataValidationError: If columns are missing or contain nulls.
    """
    missing = [c for c in RAW_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DataValidationError(f"Raw data missing columns: {missing}")
    null_cols = [c for c in RAW_REQUIRED_COLUMNS if df[c].isna().any()]
    if null_cols:
        raise DataValidationError(f"Raw data has nulls in: {null_cols}")


def build_features(df: pd.DataFrame, dropna: bool = True) -> pd.DataFrame:
    """Transform raw hourly data into the supervised modelling matrix.

    Adds calendar features, per-SKU lag/rolling features, and one-hot encodes
    ``weather`` and ``category``. Lags are computed within each ``product_id``
    group after sorting by time, so there is no cross-SKU or look-ahead leakage.

    Args:
        df: Raw frame conforming to :data:`RAW_REQUIRED_COLUMNS`.
        dropna: Drop the warm-up rows that contain NaN lag values.

    Returns:
        Feature frame including ``timestamp``, ``product_id`` and the target.
    """
    validate_raw(df)
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out = out.sort_values(["product_id", "timestamp"]).reset_index(drop=True)

    # Calendar features
    out["hour"] = out["timestamp"].dt.hour
    out["day_of_week"] = out["timestamp"].dt.dayofweek

    grp = out.groupby("product_id", group_keys=False)
    out["sales_lag_1h"] = grp["sales_volume"].shift(1)
    out["sales_lag_24h"] = grp["sales_volume"].shift(24)
    out["sales_lag_7d"] = grp["sales_volume"].shift(24 * 7)
    out["sales_roll_3h"] = grp["sales_volume"].shift(1).rolling(3, min_periods=1).mean()
    out["stock_lag_1h"] = grp["stock_level"].shift(1)

    # One-hot encodings (drop_first to avoid collinearity)
    out = pd.get_dummies(out, columns=["weather", "category"], drop_first=True, dtype=int)

    if dropna:
        out = out.dropna().reset_index(drop=True)
    return out


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Return the ordered list of model-input columns present in ``df``."""
    return [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
