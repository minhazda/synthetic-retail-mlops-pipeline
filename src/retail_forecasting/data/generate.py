"""Reproducible synthetic retail dataset generator.

Production-hardened rewrite of the original dissertation script:

* fully **seeded** (one ``numpy.random.Generator``) — identical output for a
  given seed, which is essential for reproducible experiments and CI;
* vectorised inner loop instead of per-row Python appends;
* type hints, docstrings, and a CLI entrypoint;
* path and parameters injected from config, never hard-coded.

Generates hourly demand for ``num_products`` SKUs over ``num_days`` days.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import GeneratorConfig, load_config
from ..logging_config import configure_logging, get_logger

log = get_logger(__name__)

CATEGORIES: tuple[str, ...] = ("Beverages", "Snacks", "Dairy", "Cleaning", "Fresh Produce")
WEATHER: tuple[str, ...] = ("Sunny", "Rainy", "Cloudy", "Snowy", "Cold")
_BASE_DEMAND: dict[str, float] = {
    "Beverages": 2.0,
    "Snacks": 3.0,
    "Dairy": 1.0,
    "Cleaning": 0.5,
    "Fresh Produce": 2.0,
}
_HOLIDAYS = {datetime(2025, 1, 1).date(), datetime(2025, 2, 14).date()}


def generate(cfg: GeneratorConfig) -> pd.DataFrame:
    """Generate a reproducible hourly synthetic retail dataset.

    Args:
        cfg: Generator parameters (days, products, seed, start date).

    Returns:
        A tidy DataFrame with one row per (timestamp, product_id).
    """
    rng = np.random.default_rng(cfg.seed)
    start = pd.Timestamp(cfg.start_date)
    n_hours = cfg.num_days * 24

    timestamps = pd.date_range(start, periods=n_hours, freq="h")
    product_ids = [f"P{str(i).zfill(3)}" for i in range(1, cfg.num_products + 1)]
    product_category = {pid: CATEGORIES[rng.integers(len(CATEGORIES))] for pid in product_ids}

    frames: list[pd.DataFrame] = []
    for ts in timestamps:
        hour = ts.hour
        is_holiday = int(ts.date() in _HOLIDAYS)
        weather = WEATHER[rng.integers(len(WEATHER))]
        foot_traffic = int(rng.poisson(100 if hour in (12, 18) else 50))

        cats = np.array([product_category[pid] for pid in product_ids])
        base = np.array([_BASE_DEMAND[c] for c in cats])
        is_promo = int(ts.day % 7 == 0 and hour in (10, 11, 17))
        promo = np.full(len(product_ids), is_promo)
        lam = base * np.where(promo == 1, 1.5, 1.0) * (foot_traffic / 100.0)
        sales = rng.poisson(np.clip(lam, 0, None))
        stock = np.clip(200 - sales + rng.integers(0, 5, size=len(product_ids)), 0, None)

        frames.append(
            pd.DataFrame(
                {
                    "timestamp": ts,
                    "product_id": product_ids,
                    "category": cats,
                    "sales_volume": sales.astype(int),
                    "stock_level": stock.astype(int),
                    "promo_flag": promo.astype(int),
                    "holiday_flag": is_holiday,
                    "weather": weather,
                    "foot_traffic": foot_traffic,
                }
            )
        )

    df = pd.concat(frames, ignore_index=True)
    log.info("synthetic_dataset_generated", rows=len(df), products=cfg.num_products)
    return df


def main() -> None:
    """CLI: generate the raw dataset and write it to the configured path."""
    parser = argparse.ArgumentParser(description="Generate synthetic retail data.")
    parser.add_argument("--config", default=None, help="Path to config YAML.")
    args = parser.parse_args()

    cfg = load_config(args.config)
    configure_logging(cfg.log_level)

    df = generate(cfg.generator)
    out: Path = cfg.data.raw_path
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    log.info("raw_dataset_written", path=str(out), rows=len(df))


if __name__ == "__main__":
    main()
