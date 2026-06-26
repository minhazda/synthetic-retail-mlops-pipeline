"""Offline data-drift reporting with Evidently.

Compares a *reference* feature set (e.g. the training distribution) against a
*current* batch (recent production inputs or a fresh holdout) and writes an HTML
+ JSON drift report. This is the offline complement to the live Prometheus
`rf_prediction_value` histogram exposed by the serving API.

Evidently is an optional, monitoring-only dependency (see
``requirements-monitoring.txt``); it is imported lazily inside the functions so
the serving image and the core test suite do not need it installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def align_columns(
    reference: pd.DataFrame, current: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Restrict both frames to their shared *numeric* columns.

    Evidently needs the reference and current frames to share a schema; this
    drops columns that are not present in both or are non-numeric.

    Raises:
        ValueError: if the frames share no numeric columns.
    """
    shared = [c for c in reference.columns if c in current.columns]
    ref = reference[shared].select_dtypes("number")
    cur = current[shared].select_dtypes("number")
    if ref.shape[1] == 0:
        raise ValueError("reference and current share no numeric columns")
    return ref, cur[ref.columns]


def drift_report(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    out_dir: Path | str = "reports",
) -> dict[str, Any]:
    """Build a DataDrift report, write HTML + JSON, and return the summary dict."""
    from evidently.metric_preset import DataDriftPreset
    from evidently.report import Report

    ref, cur = align_columns(reference, current)
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=ref, current_data=cur)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report.save_html(str(out / "drift_report.html"))
    summary: dict[str, Any] = report.as_dict()
    (out / "drift_report.json").write_text(
        json.dumps(summary, default=str, indent=2), encoding="utf-8"
    )
    return summary


def dataset_drift_share(summary: dict[str, Any]) -> float:
    """Pull the share of drifted columns out of an Evidently summary dict."""
    for metric in summary.get("metrics", []):
        result = metric.get("result", {})
        if "share_of_drifted_columns" in result:
            return float(result["share_of_drifted_columns"])
    raise KeyError("share_of_drifted_columns not found in Evidently summary")


def _demo() -> None:
    """Self-contained demo: reference vs a deliberately shifted current batch."""
    import numpy as np

    rng = np.random.default_rng(42)
    reference = pd.DataFrame(
        {
            "foot_traffic": rng.normal(50, 10, 1000),
            "stock_level": rng.normal(180, 30, 1000),
            "sales_lag_24h": rng.poisson(2, 1000).astype(float),
        }
    )
    current = pd.DataFrame(
        {
            "foot_traffic": rng.normal(65, 10, 1000),  # shifted up => drift
            "stock_level": rng.normal(180, 30, 1000),  # stable
            "sales_lag_24h": rng.poisson(3, 1000).astype(float),  # shifted up
        }
    )
    summary = drift_report(reference, current, out_dir="reports")
    print(f"share_of_drifted_columns = {dataset_drift_share(summary):.2f}")
    print("wrote reports/drift_report.html and reports/drift_report.json")


if __name__ == "__main__":  # pragma: no cover
    _demo()
