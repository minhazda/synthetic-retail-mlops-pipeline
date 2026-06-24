
# Synthetic Retail Dataset Generator Script
# Author: Md Minhazur Rahman
# Description: Generates 60 days of hourly data for 100 retail SKUs

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# Parameters
num_days = 60
hours_per_day = 24
num_products = 100
start_date = datetime(2025, 1, 1)

# Categories and conditions
categories = ["Beverages", "Snacks", "Dairy", "Cleaning", "Fresh Produce"]
weather_conditions = ["Sunny", "Rainy", "Cloudy", "Snowy", "Cold"]

# Generate timestamps
timestamps = [start_date + timedelta(hours=i) for i in range(num_days * hours_per_day)]

# Product catalog
product_ids = [f"P{str(i).zfill(3)}" for i in range(1, num_products + 1)]
product_categories = {pid: random.choice(categories) for pid in product_ids}

# Generate data
data = []
for timestamp in timestamps:
    hour = timestamp.hour
    is_holiday = 1 if timestamp.date() in [datetime(2025, 1, 1).date(), datetime(2025, 2, 14).date()] else 0
    weather = random.choice(weather_conditions)
    foot_traffic = np.random.poisson(100 if hour in [12, 18] else 50)

    for pid in product_ids:
        category = product_categories[pid]
        base_demand = {"Beverages": 2, "Snacks": 3, "Dairy": 1, "Cleaning": 0.5, "Fresh Produce": 2}[category]
        promo = 1 if (timestamp.day % 7 == 0 and hour in [10, 11, 17]) else 0
        sales_volume = np.random.poisson(base_demand * (1.5 if promo else 1) * (foot_traffic / 100))
        stock_level = max(0, 200 - sales_volume + np.random.randint(0, 5))

        data.append({
            "timestamp": timestamp,
            "product_id": pid,
            "category": category,
            "sales_volume": sales_volume,
            "stock_level": stock_level,
            "promo_flag": promo,
            "holiday_flag": is_holiday,
            "weather": weather,
            "foot_traffic": foot_traffic
        })

# Convert to DataFrame and export
df = pd.DataFrame(data)
df.to_csv("simulated_retail_dataset_minhazur.csv", index=False)
print("Dataset generated and saved successfully.")
