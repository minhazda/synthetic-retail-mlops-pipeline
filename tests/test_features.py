"""Tests for the shared feature pipeline: schema, leakage guards, validation."""

from __future__ import annotations

import pandas as pd
import pytest

from retail_forecasting.exceptions import DataValidationError
from retail_forecasting.features import (
    NON_FEATURE_COLUMNS,
    build_features,
    feature_columns,
    validate_raw,
)


def test_build_features_adds_lags(raw_df: pd.DataFrame) -> None:
    feats = build_features(raw_df)
    for col in ("sales_lag_1h", "sales_lag_24h", "sales_roll_3h", "hour", "day_of_week"):
        assert col in feats.columns


def test_no_nulls_after_build(raw_df: pd.DataFrame) -> None:
    feats = build_features(raw_df)
    assert not feats.isna().any().any()


def test_feature_columns_excludes_identifiers(raw_df: pd.DataFrame) -> None:
    feats = build_features(raw_df)
    cols = feature_columns(feats)
    for excluded in NON_FEATURE_COLUMNS:
        assert excluded not in cols


def test_lags_are_per_sku(raw_df: pd.DataFrame) -> None:
    # The first observation of each SKU must not borrow from another SKU.
    feats = build_features(raw_df, dropna=False)
    first_rows = feats.groupby("product_id").head(1)
    assert first_rows["sales_lag_1h"].isna().all()


def test_validate_raw_rejects_missing_columns() -> None:
    bad = pd.DataFrame({"timestamp": [1], "product_id": ["P001"]})
    with pytest.raises(DataValidationError):
        validate_raw(bad)
