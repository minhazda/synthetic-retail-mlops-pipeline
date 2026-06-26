# Observability

Two complementary layers monitor the forecasting service:

## 1. Live metrics (Prometheus + Grafana)

The API exposes Prometheus metrics at **`/metrics`** via
`prometheus-fastapi-instrumentator`:

| Metric | Type | Meaning |
|--------|------|---------|
| `http_requests_total` | counter | Requests by handler/method/status |
| `http_request_duration_seconds` | histogram | Request latency (drives p95) |
| `rf_predictions_total` | counter | Prediction rows served |
| `rf_prediction_value` | histogram | Distribution of predicted demand (model-side drift signal) |

Run the stack locally:

```bash
# 1. Serve the API (repo root)
docker compose up api                # http://localhost:8000

# 2. Start Prometheus + Grafana (this folder)
docker compose -f monitoring/docker-compose.monitoring.yml up
```

- Grafana: <http://localhost:3000> (anonymous viewer; `admin`/`admin` to edit) —
  the **Retail Forecasting API** dashboard is auto-provisioned.
- Prometheus: <http://localhost:9090>

Generate some traffic (`curl` the `/predict` example from the root README) and
the panels populate: request rate, p95 latency, prediction throughput, and the
predicted-value quantiles.

The live Cloud Run service also serves `/metrics`; uncomment the `cloudrun` job
in [`prometheus.yml`](prometheus.yml) to scrape it directly.

## 2. Offline data drift (Evidently)

`retail_forecasting.monitoring.drift` builds an Evidently **DataDrift** report
comparing a reference distribution against a current batch:

```bash
pip install -r requirements-monitoring.txt
python -m retail_forecasting.monitoring.drift   # demo: writes reports/drift_report.html
```

Use it in a batch job (`drift_report(reference_df, current_df)`) to alert when
`dataset_drift_share(...)` crosses a threshold, then trigger retraining.
