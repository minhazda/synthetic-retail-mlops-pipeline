# syntax=docker/dockerfile:1.7
# ===========================================================================
# Multi-stage build for the Retail Demand Forecasting pipeline.
#
#   Stage 1 (builder): create a venv and compile/install pinned wheels.
#   Stage 2 (runtime): copy only the venv + source -> small, non-root image.
#
# One image, three roles via the entrypoint: generate | train | serve | app.
#   docker build -t retail-forecasting .
#   docker run --rm retail-forecasting train
#   docker run --rm -p 8000:8000 retail-forecasting serve
# ===========================================================================

# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Build-time deps for LightGBM (libgomp) and wheel building.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN python -m venv "$VIRTUAL_ENV"

WORKDIR /app
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 — runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="retail-forecasting" \
      org.opencontainers.image.description="Production MLOps pipeline for retail demand forecasting." \
      org.opencontainers.image.authors="Md Minhazur Rahman <minhazurrahman.ds@gmail.com>" \
      org.opencontainers.image.source="https://github.com/minhazur/retail-forecasting"

# Runtime shared lib for LightGBM + curl for the healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    RF_CONFIG=/app/configs/config.yaml \
    RF_MODEL_PATH=/app/models/lgbm_model.joblib \
    API_PORT=8000 \
    STREAMLIT_PORT=8501

# Copy the prepared virtualenv from the builder.
COPY --from=builder /opt/venv /opt/venv

# Create an unprivileged user and writable runtime dirs.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data /app/models /app/mlruns \
    && chown -R appuser:appuser /app

WORKDIR /app

# Copy source last (most frequently changed) to maximise layer caching.
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser configs/ ./configs/
COPY --chown=appuser:appuser docker/entrypoint.sh ./docker/entrypoint.sh
COPY --chown=appuser:appuser pyproject.toml README.md ./

RUN chmod +x ./docker/entrypoint.sh

USER appuser

EXPOSE 8000 8501

# Liveness probe for the inference API (overridden/ignored for batch roles).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${API_PORT}/health" || exit 1

ENTRYPOINT ["./docker/entrypoint.sh"]
CMD ["serve"]
