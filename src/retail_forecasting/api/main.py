"""FastAPI real-time inference service.

Scaffold for the Week-3 deliverable that will replace the Streamlit prototype.
It loads the persisted ``joblib`` artifact (model + feature schema) lazily on
startup and exposes:

* ``GET  /health``  — liveness/readiness probe (used by Docker HEALTHCHECK);
* ``GET  /metadata`` — model + feature info;
* ``POST /predict``  — batch prediction over pre-engineered feature rows.

Feature engineering for raw payloads will be wired in alongside the training
reconciliation; for now ``/predict`` accepts rows already matching the model's
feature schema, which keeps the contract explicit and testable.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from ..exceptions import FeatureMismatchError, ModelNotFoundError
from ..logging_config import configure_logging, get_logger

log = get_logger(__name__)

MODEL_PATH = Path(os.environ.get("RF_MODEL_PATH", "models/lgbm_model.joblib"))

# Module-level model holder, populated on startup.
_STATE: dict[str, Any] = {"model": None, "features": []}


def _load_model(path: Path | None = None) -> None:
    """Load the persisted model artifact into module state.

    Resolves ``MODEL_PATH`` at call time (not import time) so tests and runtime
    overrides take effect.

    Raises:
        ModelNotFoundError: If the artifact file is missing or unreadable.
    """
    path = path or MODEL_PATH
    if not path.is_file():
        raise ModelNotFoundError(f"Model artifact not found at {path}")
    bundle = joblib.load(path)
    _STATE["model"] = bundle["model"]
    _STATE["features"] = list(bundle["features"])
    log.info("model_loaded", path=str(path), n_features=len(_STATE["features"]))


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Load the model on startup; degrade gracefully if it is absent."""
    configure_logging(os.environ.get("RF_LOG_LEVEL", "INFO"))
    try:
        _load_model()
    except ModelNotFoundError as exc:
        # Service still starts so /health can report 'model not loaded';
        # /predict will return 503 until a model is trained and mounted.
        log.warning("startup_without_model", error=str(exc))
    yield


app = FastAPI(
    title="Retail Demand Forecasting API",
    version="0.1.0",
    description="Real-time demand forecasts from the LightGBM pipeline.",
    lifespan=lifespan,
)


class PredictRequest(BaseModel):
    """Batch of pre-engineered feature rows."""

    rows: list[dict[str, float]] = Field(
        ..., min_length=1, description="Each dict maps feature name -> value."
    )


class PredictResponse(BaseModel):
    """Prediction output."""

    # ``model_version`` would otherwise collide with pydantic's protected
    # ``model_`` namespace and emit a UserWarning; opt out explicitly.
    model_config = ConfigDict(protected_namespaces=())

    predictions: list[float]
    model_version: str = "0.1.0"


@app.get("/health")
def health() -> dict[str, Any]:
    """Liveness/readiness probe."""
    return {"status": "ok", "model_loaded": _STATE["model"] is not None}


@app.get("/metadata")
def metadata() -> dict[str, Any]:
    """Return model feature schema and basic metadata."""
    if _STATE["model"] is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model not loaded."
        )
    return {"n_features": len(_STATE["features"]), "features": _STATE["features"]}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    """Predict demand for a batch of feature rows.

    Raises:
        HTTPException: 503 if no model is loaded; 422 on feature mismatch.
    """
    model = _STATE["model"]
    features: list[str] = _STATE["features"]
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model not loaded."
        )

    frame = pd.DataFrame(req.rows)
    missing = [f for f in features if f not in frame.columns]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing features: {missing}",
        )
    try:
        ordered = frame[features]
    except KeyError as exc:  # pragma: no cover - guarded above
        raise FeatureMismatchError(str(exc)) from exc

    preds = model.predict(ordered)
    return PredictResponse(predictions=[float(p) for p in preds])
