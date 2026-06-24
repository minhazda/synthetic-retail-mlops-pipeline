"""Shared pytest fixtures."""

from __future__ import annotations

import pandas as pd
import pytest

from retail_forecasting.config import GeneratorConfig
from retail_forecasting.data.generate import generate


@pytest.fixture(scope="session")
def small_generator_config() -> GeneratorConfig:
    """A tiny, fast generator config for tests."""
    return GeneratorConfig(num_days=10, num_products=5, seed=7, start_date="2025-01-01")


@pytest.fixture(scope="session")
def raw_df(small_generator_config: GeneratorConfig) -> pd.DataFrame:
    """A small reproducible raw dataset."""
    return generate(small_generator_config)
