# streamlit_retail_prototype.py
# Retail Demand Forecasting Prototype (clean, robust)
# Minhazur MSc Project — Streamlit app

import io
import sys
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor

# Optional models (graceful fallback)
try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except Exception:
    HAS_XGB = False

try:
    from lightgbm import LGBMRegressor
    HAS_LGBM = True
except Exception:
    HAS_LGBM = False


# ---------------------------
# Helpers
# ---------------------------

@st.cache_data(show_spinner=False)
def make_synthetic(n_days: int = 420, n_skus: int = 12, seed: int = 42) -> pd.DataFrame:
    """
    Generate simple daily synthetic retail data with seasonality, trend, promotions, and holidays.
    Columns: date, sku, sales, price, promo, holiday
    """
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2023-01-01")
    dates = pd.date_range(start, periods=n_days, freq="D")

    skus = [f"P{str(i+1).zfill(3)}" for i in range(n_skus)]
    base = rng.integers(40, 90, size=n_skus)  # base demand per SKU
    trend = np.linspace(0, 12, n_days)        # gentle upward trend

    all_rows = []
    # simple holiday windows (Dec season + a summer bump)
    holiday_days = set(pd.date_range("2023-12-10", "2023-12-31", freq="D")).union(
        set(pd.date_range("2024-07-01", "2024-07-07", freq="D"))
    )

    for si, sku in enumerate(skus):
        # weekly seasonality: higher on Fri/Sat
        weekly = (np.sin(np.arange(n_days) * 2 * np.pi / 7) + 1.5)

        # random promo periods
        promo_mask = np.zeros(n_days, dtype=int)
        for _ in range(5):
            start_ix = rng.integers(0, n_days - 7)
            promo_mask[start_ix:start_ix+7] = 1

        # price fluctuates mildly (inverse to promo)
        base_price = rng.uniform(8.0, 18.0)
        price = base_price + rng.normal(0, 0.4, size=n_days) - 0.6 * promo_mask

        # holiday effect
        holiday_mask = np.array([1 if d in holiday_days else 0 for d in dates])

        # sales = base + seasonality + trend + promo uplift + holiday uplift + noise
        mu = (
            base[si]
            + 4.0 * weekly
            + trend
            + 8.0 * promo_mask
            + 6.0 * holiday_mask
        )
        sales = np.maximum(
            0,
            np.round(mu + rng.normal(0, 6.0, size=n_days))
        ).astype(int)

        df_sku = pd.DataFrame({
            "date": dates,
            "sku": sku,
            "sales": sales,
            "price": np.round(price, 2),
            "promo": promo_mask,
            "holiday": holiday_mask
        })
        all_rows.append(df_sku)

    df = pd.concat(all_rows, ignore_index=True)
    return df


def clean_input(df: pd.DataFrame) -> pd.DataFrame:
    # Standardize column names
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    # Flexible date col: try 'date' or 'timestamp'
    date_col = "date" if "date" in df.columns else ("timestamp" if "timestamp" in df.columns else None)
    if date_col is None:
        raise ValueError("CSV must include a 'date' (or 'timestamp') column.")

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.rename(columns={date_col: "date"})
    # Required
    for col in ["sku", "sales"]:
        if col not in df.columns:
            raise ValueError(f"CSV must include column '{col}'.")
    # Optional
    for opt in ["price", "promo", "holiday"]:
        if opt not in df.columns:
            df[opt] = 0
    # sort
    df = df.sort_values(["sku", "date"]).reset_index(drop=True)
    return df


def build_features(df: pd.DataFrame,
                   sku: str,
                   lags: List[int] = [1, 7, 14],
                   roll_windows: List[int] = [7]) -> pd.DataFrame:
    """Create per-SKU supervised learning features on daily data."""
    sdf = df[df["sku"] == sku].sort_values("date").copy()

    # Time features
    sdf["dow"] = sdf["date"].dt.dayofweek
    sdf["month"] = sdf["date"].dt.month

    # Lags
    for L in lags:
        sdf[f"lag_{L}"] = sdf["sales"].shift(L)

    # Rolling means
    for W in roll_windows:
        sdf[f"roll_mean_{W}"] = sdf["sales"].shift(1).rolling(W, min_periods=1).mean()

    # Ensure numeric types
    for c in ["promo", "holiday"]:
        if c in sdf.columns:
            sdf[c] = pd.to_numeric(sdf[c], errors="coerce").fillna(0).astype(int)
        else:
            sdf[c] = 0

    # Drop initial NA rows from lagging
    sdf = sdf.dropna().reset_index(drop=True)
    return sdf


def train_eval_forecast(
    df: pd.DataFrame,
    sku: str,
    model_name: str = "Random Forest",
    feature_cols: Optional[List[str]] = None,
    forecast_horizon: int = 14,
    promo_toggle: str = "No change",
    holiday_toggle: str = "No change",
) -> Dict[str, any]:
    """
    Train on first 80% of history (time split), evaluate on last 20%, then forecast next N days.
    """
    sdf = df[df["sku"] == sku].sort_values("date").copy()
    if feature_cols is None:
        feature_cols = [c for c in sdf.columns if c not in ["date", "sku", "sales"]]

    # Time-based split
    n = len(sdf)
    if n < 30:
        raise ValueError("Not enough history for training. Provide at least 30 rows per SKU.")
    split_ix = int(0.8 * n)
    train_df = sdf.iloc[:split_ix]
    test_df = sdf.iloc[split_ix:]

    X_train = train_df[feature_cols].values
    y_train = train_df["sales"].values
    X_test = test_df[feature_cols].values
    y_test = test_df["sales"].values

    # Model selector
    if model_name == "Random Forest":
        model = RandomForestRegressor(
            n_estimators=300, max_depth=None, random_state=123, n_jobs=-1
        )
    elif model_name == "Linear Regression":
        model = LinearRegression()
    elif model_name == "XGBoost (if available)" and HAS_XGB:
        model = XGBRegressor(
            n_estimators=500, learning_rate=0.05, max_depth=5,
            subsample=0.8, colsample_bytree=0.8, random_state=123
        )
    elif model_name == "LightGBM (if available)" and HAS_LGBM:
        model = LGBMRegressor(
            n_estimators=500, learning_rate=0.05, max_depth=-1,
            subsample=0.8, colsample_bytree=0.8, random_state=123
        )
    else:
        # fallback
        model = RandomForestRegressor(
            n_estimators=300, random_state=123, n_jobs=-1
        )

    model.fit(X_train, y_train)

    # Evaluate (avoid 'squared' kw for broad sklearn compat)
    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mape = float(np.mean(np.abs((y_test - y_pred) / np.clip(y_test, 1, None))) * 100)

    # Recursive N‑day forecast with scenario toggles
    hist = sdf.copy()
    last_date = hist["date"].iloc[-1]
    future = []
    current = hist.copy()

    for step in range(forecast_horizon):
        next_date = last_date + pd.Timedelta(days=step + 1)

        # Scenario toggles during forecast window
        promo_val = current["promo"].iloc[-1]
        hol_val = 1 if next_date.month == 12 else 0  # seasonal default

        if promo_toggle == "Force ON":
            promo_val = 1
        elif promo_toggle == "Force OFF":
            promo_val = 0

        if holiday_toggle == "Force ON (Dec-like)":
            hol_val = 1
        elif holiday_toggle == "Force OFF":
            hol_val = 0

        # Build a single-row feature vector like build_features() result
        tmp = current.tail(20).copy()  # ensure lags compute
        # Prepare minimal frame for the new row (sales initially NA)
        new_row = {
            "date": next_date, "sku": sku,
            "sales": np.nan,
            "price": current["price"].iloc[-1] if "price" in current.columns else 10.0,
            "promo": promo_val,
            "holiday": hol_val
        }
        tmp = pd.concat([tmp, pd.DataFrame([new_row])], ignore_index=True)

        # Recompute features on tmp (uses lags/rolling)
        tmp_feat = build_features(tmp, sku, lags=[1,7,14], roll_windows=[7])
        x_cols = [c for c in tmp_feat.columns if c not in ["date","sku","sales"]]
        x_vec = tmp_feat.iloc[-1:][x_cols].values
        y_next = float(max(0, np.round(model.predict(x_vec)[0])))

        # append finalized row
        future.append({"date": next_date, "sku": sku, "sales": y_next,
                       "price": new_row["price"], "promo": promo_val, "holiday": hol_val})

        # add to current history so next step can lag from it
        realized = pd.DataFrame([{
            "date": next_date, "sku": sku, "sales": y_next,
            "price": new_row["price"], "promo": promo_val, "holiday": hol_val
        }])
        current = pd.concat([current, realized], ignore_index=True)

    future_df = pd.DataFrame(future)
    return {
        "model": model,
        "feature_cols": feature_cols,
        "train_df": train_df,
        "test_df": test_df.assign(pred=y_pred),
        "metrics": {"MAE": mae, "RMSE": rmse, "MAPE (%)": mape},
        "forecast_df": future_df
    }


def make_figure(train_df: pd.DataFrame,
                test_df: pd.DataFrame,
                forecast_df: pd.DataFrame,
                split_date: pd.Timestamp) -> go.Figure:
    fig = go.Figure()

    # History (actuals)
    fig.add_trace(go.Scatter(
        x=train_df["date"], y=train_df["sales"],
        mode="lines", name="Actual (Train)", line=dict(width=1.6)
    ))

    # Test actuals
    fig.add_trace(go.Scatter(
        x=test_df["date"], y=test_df["sales"],
        mode="lines", name="Actual (Test)", line=dict(width=1.6)
    ))

    # Test predictions
    fig.add_trace(go.Scatter(
        x=test_df["date"], y=test_df["pred"],
        mode="lines", name="Predicted (Test)", line=dict(width=2, dash="dash")
    ))

    # Next horizon forecast
    fig.add_trace(go.Scatter(
        x=forecast_df["date"], y=forecast_df["sales"],
        mode="lines+markers", name="Forecast (Next)", line=dict(width=2)
    ))

    # Robust split marker (no Timestamp math)
    split_x = pd.to_datetime(split_date).to_pydatetime()
    fig.add_shape(
        type="line",
        x0=split_x, x1=split_x,
        y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(width=2, dash="dot", color="gray")
    )
    fig.add_annotation(
        x=split_x, y=1.02,
        xref="x", yref="paper",
        text="Train/Test split",
        showarrow=False
    )

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=30, r=20, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis_title="Date", yaxis_title="Units",
        title="Actuals vs Predicted & Forecast"
    )
    return fig


def render_feature_importance(model, feature_cols: List[str]):
    try:
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            order = np.argsort(importances)[::-1]
            top_k = min(12, len(feature_cols))
            imp_df = pd.DataFrame({
                "Feature": np.array(feature_cols)[order][:top_k],
                "Importance": importances[order][:top_k]
            })
            fig = go.Figure(go.Bar(x=imp_df["Feature"], y=imp_df["Importance"]))
            fig.update_layout(
                template="plotly_dark",
                title="Top Feature Importances",
                xaxis_title="Feature", yaxis_title="Importance",
                margin=dict(l=30, r=20, t=50, b=80)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Selected model does not expose feature importances.")
    except Exception as e:
        st.warning(f"Could not render feature importances: {e}")


# ---------------------------
# Streamlit App
# ---------------------------

st.set_page_config(page_title="Retail Demand Forecasting Prototype",
                   layout="wide",
                   initial_sidebar_state="expanded")

st.sidebar.title("Data & Settings")

uploaded = st.sidebar.file_uploader(
    "Upload CSV (needs: date, sku, sales; optional: price, promo, holiday)",
    type=["csv"], accept_multiple_files=False
)

use_synth = st.sidebar.checkbox("Or use built-in synthetic data", value=True)

# Load data
if uploaded is not None:
    try:
        raw = pd.read_csv(uploaded)
        df_raw = clean_input(raw)
    except Exception as e:
        st.sidebar.error(f"Error reading CSV: {e}")
        st.stop()
elif use_synth:
    df_raw = make_synthetic()
else:
    st.sidebar.warning("Please upload a CSV or tick synthetic data.")
    st.stop()

all_skus = sorted(df_raw["sku"].unique().tolist())
sku = st.sidebar.selectbox("Select SKU", options=all_skus, index=0)

# Models list (show conditionals)
model_options = ["Random Forest", "Linear Regression"]
if HAS_XGB:
    model_options.append("XGBoost (if available)")
if HAS_LGBM:
    model_options.append("LightGBM (if available)")
model_name = st.sidebar.selectbox("Model", options=model_options, index=0)

horizon = st.sidebar.slider("Forecast horizon (days)", 7, 30, 14, step=1)

promo_flag = st.sidebar.selectbox("Promo during forecast?",
                                  ["No change", "Force ON", "Force OFF"], index=0)

holiday_flag = st.sidebar.selectbox("Holiday during forecast?",
                                    ["No change", "Force ON (Dec-like)", "Force OFF"], index=0)

st.sidebar.caption("Tip: Upload a CSV with columns **date, sku, sales** (+ optional **price, promo, holiday**). "
                   "Dates should be YYYY-MM-DD. The app splits the last 20% of history for testing to avoid look-ahead leakage.")

# Main header
st.title(f"Actual vs Predicted & Forecast — {sku}")

# Build features for the chosen SKU
df_feat = build_features(df_raw, sku, lags=[1,7,14], roll_windows=[7])

if len(df_feat) < 30:
    st.warning("Not enough data after feature building. Try another SKU or provide more history.")
    st.stop()

feature_cols = [c for c in df_feat.columns if c not in ["date", "sku", "sales"]]

# Train + Evaluate + Forecast
results = train_eval_forecast(
    df=df_feat,
    sku=sku,
    model_name=model_name,
    feature_cols=feature_cols,
    forecast_horizon=horizon,
    promo_toggle=promo_flag,
    holiday_toggle=holiday_flag
)

train_df = results["train_df"]
test_df = results["test_df"]
forecast_df = results["forecast_df"]
metrics = results["metrics"]
split_date = test_df["date"].iloc[0]

# Plot
fig = make_figure(train_df, test_df, forecast_df, split_date)
st.plotly_chart(fig, use_container_width=True)

# Metrics panel
with st.sidebar:
    st.subheader("Metrics (last 20% of history)")
    st.metric("MAE", f"{metrics['MAE']:.2f}")
    st.metric("RMSE", f"{metrics['RMSE']:.2f}")
    st.metric("MAPE (%)", f"{metrics['MAPE (%)']:.2f}")
    st.caption("Time-based split; no look-ahead leakage.")

# Scenario explanation
st.subheader("Scenario toggles")
st.markdown(
    """
- **Promo**: Forces promotional flag during the forecast window to simulate uplift.  
- **Holiday**: Forces holiday flag (e.g., December seasonality) during forecast.  
    """
)

# Feature importance if available
st.divider()
st.subheader("Model explainability")
render_feature_importance(results["model"], results["feature_cols"])

# Data peek (collapsible)
with st.expander("Show last 10 rows used for training features"):
    st.dataframe(df_feat.tail(10), use_container_width=True)

st.caption("© MSc Project – Retail Demand Forecasting Prototype")
