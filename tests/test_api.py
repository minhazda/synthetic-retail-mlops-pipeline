"""Tests for the FastAPI service, including the no-model degraded path."""

from __future__ import annotations

import joblib
from fastapi.testclient import TestClient

from retail_forecasting.api import main as api_main


def test_health_without_model(monkeypatch) -> None:
    monkeypatch.setitem(api_main._STATE, "model", None)
    monkeypatch.setitem(api_main._STATE, "features", [])
    with TestClient(api_main.app) as client:
        # lifespan tries to load a model from disk; in CI none exists -> 200 ok.
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_predict_requires_model(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "_load_model", lambda *a, **k: None)
    with TestClient(api_main.app) as client:
        api_main._STATE["model"] = None
        resp = client.post("/predict", json={"rows": [{"x": 1.0}]})
        assert resp.status_code == 503


def test_predict_with_stub_model(tmp_path, monkeypatch) -> None:
    class _Stub:
        def predict(self, frame):
            return [42.0] * len(frame)

    artifact = tmp_path / "m.joblib"
    joblib.dump({"model": _Stub(), "features": ["a", "b"]}, artifact)
    # Point the API at our stub artifact; lifespan loads it on startup.
    monkeypatch.setattr(api_main, "MODEL_PATH", artifact)

    with TestClient(api_main.app) as client:
        resp = client.post("/predict", json={"rows": [{"a": 1.0, "b": 2.0}]})
        assert resp.status_code == 200
        assert resp.json()["predictions"] == [42.0]

        bad = client.post("/predict", json={"rows": [{"a": 1.0}]})
        assert bad.status_code == 422
