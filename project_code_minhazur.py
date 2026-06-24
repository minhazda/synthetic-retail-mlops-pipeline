
# -------------------------------
# Project: Real-Time Retail Demand Forecasting
# Student: Md Minhazur Rahman
# Supervisor: Dr. Tuan Vuong
# -------------------------------

# Required Libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

# -------------------------------
# 1. Load Processed Dataset
# -------------------------------
df = pd.read_csv("processed_retail_dataset_minhazur.csv", parse_dates=["timestamp"])

# -------------------------------
# 2. Feature Engineering
# -------------------------------
# Already included features in the processed dataset:
# - sales_lag_1h, sales_lag_24h, sales_lag_7d
# - sales_roll_3h, stock_lag_1h
# - One-hot encoded weather
# - Categorical: promo_flag, holiday_flag, category (encoded)
# - Time: hour, day_of_week

# -------------------------------
# 3. Exploratory Data Analysis
# -------------------------------
# Histogram
plt.figure(figsize=(8, 5))
sns.histplot(df['sales_volume'], bins=30, kde=True)
plt.title("Distribution of Sales Volume")
plt.xlabel("Sales Volume")
plt.ylabel("Frequency")
plt.savefig("sales_volume_distribution.png")
plt.close()

# Correlation Heatmap
plt.figure(figsize=(10, 6))
corr = df[['sales_volume', 'stock_level', 'foot_traffic', 'sales_lag_1h', 'sales_lag_24h',
           'sales_lag_7d', 'sales_roll_3h', 'stock_lag_1h']].corr()
sns.heatmap(corr, annot=True, cmap='coolwarm')
plt.title("Correlation Matrix")
plt.savefig("correlation_matrix.png")
plt.close()

# Time Series Plot for Product P001
sample_product = df[df["product_id"] == "P001"]
plt.figure(figsize=(10, 5))
plt.plot(sample_product["timestamp"], sample_product["sales_volume"])
plt.title("Hourly Sales Trend for Product P001")
plt.xlabel("Time")
plt.ylabel("Sales Volume")
plt.xticks(rotation=45)
plt.savefig("timeseries_product_P001.png")
plt.close()

# Day of Week Plot
plt.figure(figsize=(8, 4))
sns.barplot(data=df, x="day_of_week", y="sales_volume")
plt.title("Average Sales Volume by Day of Week")
plt.savefig("category_sales_plot.png")
plt.close()

# -------------------------------
# 4. Model Training: Random Forest
# -------------------------------
product_df = df[df["product_id"] == "P001"]
features = [
    'sales_lag_1h', 'sales_lag_24h', 'sales_lag_7d',
    'sales_roll_3h', 'stock_level', 'stock_lag_1h',
    'foot_traffic', 'promo_flag', 'holiday_flag'
]
X = product_df[features]
y = product_df["sales_volume"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# Train and Evaluate Random Forest
rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)
y_pred_rf = rf.predict(X_test)

# Metrics
mae_rf = mean_absolute_error(y_test, y_pred_rf)
rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))

# Plot: Predicted vs Actual
plt.figure(figsize=(10, 5))
plt.plot(y_test.reset_index(drop=True), label='Actual Sales')
plt.plot(y_pred_rf, label='Predicted Sales')
plt.legend()
plt.title("Predicted vs Actual Sales (RF) – Product P001")
plt.savefig("rf_pred_vs_actual.png")
plt.close()

# Feature Importance
importances = rf.feature_importances_
feat_imp_df = pd.DataFrame({"Feature": features, "Importance": importances}).sort_values(by="Importance", ascending=False)

plt.figure(figsize=(8, 5))
sns.barplot(data=feat_imp_df, x="Importance", y="Feature", palette="viridis")
plt.title("Feature Importance – Random Forest")
plt.savefig("feature_importance_rf.png")
plt.close()

# -------------------------------
# 5. Linear Regression (for comparison)
# -------------------------------
lr = LinearRegression()
lr.fit(X_train, y_train)
y_pred_lr = lr.predict(X_test)
mae_lr = mean_absolute_error(y_test, y_pred_lr)
rmse_lr = np.sqrt(mean_squared_error(y_test, y_pred_lr))

# -------------------------------
# End of Script
# -------------------------------
