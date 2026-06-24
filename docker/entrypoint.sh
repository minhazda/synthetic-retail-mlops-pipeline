#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Container entrypoint. The same image runs three roles depending on the
# first argument, so dev/CI/prod all share one build:
#
#   generate  -> create the synthetic raw dataset
#   train     -> run the training pipeline (writes model + MLflow run)
#   serve     -> start the FastAPI inference API (default)
#   app       -> start the Streamlit dashboard
#
# Any unrecognised command is exec'd verbatim (e.g. `bash`, `pytest`).
# ---------------------------------------------------------------------------
set -euo pipefail

CMD="${1:-serve}"
shift || true

case "$CMD" in
  generate)
    exec python -m retail_forecasting.data.generate "$@"
    ;;
  train)
    exec python -m retail_forecasting.train "$@"
    ;;
  serve)
    exec uvicorn retail_forecasting.api.main:app \
      --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}" "$@"
    ;;
  app)
    exec streamlit run src/retail_forecasting/app/streamlit_app.py \
      --server.port "${STREAMLIT_PORT:-8501}" --server.address 0.0.0.0 "$@"
    ;;
  *)
    exec "$CMD" "$@"
    ;;
esac
