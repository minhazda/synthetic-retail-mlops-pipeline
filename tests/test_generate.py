"""Tests for the synthetic data generator: shape, schema, reproducibility."""

from __future__ import annotations

import pandas as pd

from retail_forecasting.config import GeneratorConfig
from retail_forecasting.data.generate import generate
from retail_forecasting.features import RAW_REQUIRED_COLUMNS


def test_generate_shape(small_generator_config: GeneratorConfig) -> None:
    df = generate(small_generator_config)
    expected = small_generator_config.num_days * 24 * small_generator_config.num_products
    assert len(df) == expected


def test_generate_has_required_columns(raw_df: pd.DataFrame) -> None:
    for col in RAW_REQUIRED_COLUMNS:
        assert col in raw_df.columns


def test_generate_is_reproducible(small_generator_config: GeneratorConfig) -> None:
    a = generate(small_generator_config)
    b = generate(small_generator_config)
    pd.testing.assert_frame_equal(a, b)


def test_generate_differs_with_seed() -> None:
    a = generate(GeneratorConfig(num_days=5, num_products=3, seed=1))
    b = generate(GeneratorConfig(num_days=5, num_products=3, seed=2))
    assert not a["sales_volume"].equals(b["sales_volume"])


def test_no_negative_values(raw_df: pd.DataFrame) -> None:
    assert (raw_df["sales_volume"] >= 0).all()
    assert (raw_df["stock_level"] >= 0).all()
