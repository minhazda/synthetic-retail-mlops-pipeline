"""Unit tests for the training module's metric helpers.

These cover the pure metric/baseline logic without training a model, so they
run in milliseconds while exercising the code paths behind the README's
headline numbers.
"""

from __future__ import annotations

import numpy as np

from retail_forecasting.train import _baseline_metrics, _evaluate


def test_evaluate_perfect_prediction_is_zero_error() -> None:
    """A perfect forecast yields zero MAE/RMSE/MAPE."""
    y = np.array([1.0, 2.0, 3.0, 4.0])
    out = _evaluate(y, y.copy())
    assert out["mae"] == 0.0
    assert out["rmse"] == 0.0
    assert out["mape"] == 0.0


def test_evaluate_known_values() -> None:
    """MAE/RMSE match hand-computed values for a small example."""
    y_true = np.array([2.0, 4.0])
    y_pred = np.array([4.0, 4.0])  # errors: 2, 0
    out = _evaluate(y_true, y_pred)
    assert out["mae"] == 1.0  # (2 + 0) / 2
    assert round(out["rmse"], 6) == round(float(np.sqrt(2.0)), 6)  # sqrt((4+0)/2)


def test_baseline_metrics_reports_reduction() -> None:
    """A perfect model against a poor baseline gives a 100% reduction."""
    y = np.array([2.0, 2.0, 2.0, 2.0])
    model_metrics = _evaluate(y, y.copy())  # perfect -> mae 0
    baseline_pred = np.zeros_like(y)  # naive guess of 0 everywhere
    out = _baseline_metrics(y, baseline_pred, model_metrics)
    assert out["baseline_mae"] == 2.0
    assert out["mae_reduction_pct"] == 100.0
    assert out["rmse_reduction_pct"] == 100.0


def test_baseline_metrics_handles_zero_baseline_error() -> None:
    """When the baseline is already perfect, reduction is 0% (no divide-by-zero)."""
    y = np.array([1.0, 2.0, 3.0])
    model_metrics = _evaluate(y, y.copy())
    out = _baseline_metrics(y, y.copy(), model_metrics)
    assert out["mae_reduction_pct"] == 0.0
    assert out["rmse_reduction_pct"] == 0.0
