"""Tests for the offline drift-reporting helpers.

The column-alignment logic is tested without Evidently installed; the full
report test is skipped unless the optional dependency is present.
"""

from __future__ import annotations

import pandas as pd
import pytest

from retail_forecasting.monitoring import drift


def test_align_columns_keeps_shared_numeric() -> None:
    ref = pd.DataFrame({"a": [1, 2], "b": ["x", "y"], "c": [1.0, 2.0]})
    cur = pd.DataFrame({"a": [3, 4], "c": [3.0, 4.0], "d": [1, 2]})
    r, c = drift.align_columns(ref, cur)
    assert list(r.columns) == ["a", "c"]
    assert list(c.columns) == ["a", "c"]


def test_align_columns_raises_without_overlap() -> None:
    with pytest.raises(ValueError):
        drift.align_columns(pd.DataFrame({"a": [1]}), pd.DataFrame({"z": [1]}))


def test_dataset_drift_share_parses_summary() -> None:
    summary = {"metrics": [{"result": {"share_of_drifted_columns": 0.5}}]}
    assert drift.dataset_drift_share(summary) == 0.5


def test_drift_report_runs_if_evidently_present(tmp_path) -> None:
    pytest.importorskip("evidently")
    import numpy as np

    rng = np.random.default_rng(0)
    ref = pd.DataFrame({"x": rng.normal(0, 1, 400), "y": rng.normal(5, 2, 400)})
    cur = pd.DataFrame({"x": rng.normal(2, 1, 400), "y": rng.normal(5, 2, 400)})
    summary = drift.drift_report(ref, cur, out_dir=tmp_path)
    assert (tmp_path / "drift_report.html").exists()
    assert 0.0 <= drift.dataset_drift_share(summary) <= 1.0
