# Retail Demand Forecasting API — Portfolio Case Study

## Problem

Retailers lose revenue when they over- or under-stock products — a problem that
compounds at scale across hundreds of SKUs, stores, and time slots. Accurate
demand forecasting at the hour level lets procurement and logistics teams act
before a shortage or surplus becomes visible.

## Approach

Real transaction data carries customer privacy risk, so this project generates a
**synthetic dataset** that has the same statistical shape as real retail data but
contains no genuine records. From that dataset, a set of time-aware features is
built — things like sales in the previous hour, rolling averages, promotional
flags, weather conditions, and product category — with care taken to avoid
**data leakage**: no information that would only be available after the fact is
used to train the model.

The forecasting model is a gradient-boosted tree (LightGBM), validated on a
**time-ordered train/test split** that prevents look-ahead leakage and reflects
the conditions a deployed model would actually face. A seasonal-naive baseline
(same hour, previous day) is computed on the same holdout set to give the
accuracy numbers context.

The trained artifact is baked directly into a Docker image at build time, so the
live service loads it instantly rather than retraining on every boot. The service
is a typed **FastAPI** application with a `/predict` endpoint, a health check,
and auto-generated docs, running behind a CI/CD pipeline (GitHub Actions) that
enforces linting, type-checking, and a test suite on every commit.

## Result

The model reduces MAE by **~41%** compared to a seasonal-naive baseline (same
hour, previous day) on a held-out test set — reproduced by running
`python -m retail_forecasting.train` with a fixed seed (42).

Other verifiable facts:

- **Live API** deployed at `https://minhazda-retail-forecasting-api.hf.space`
- **Test suite** runs on every push; coverage reported via Codecov
- **Fully typed** — all functions carry annotations verified by mypy in CI
- **Reproducible** — same seed, same data generator, same model every time

## What I Would Do Next in Production

- **Monitoring:** log prediction distributions and alert when input features
  drift from the training distribution (e.g. a promotional pattern the model
  has never seen)
- **Model registry:** version artifacts in MLflow so a rollback is one command,
  not a rebuild
- **A/B rollout:** shadow a new model against the production model on live
  traffic before cutting over, controlled by a feature flag
