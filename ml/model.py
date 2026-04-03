import os
import runpy

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

_DIR = os.path.dirname(__file__)
_DATA_PATH = os.path.join(_DIR, "data.csv")

# Load dataset (auto-generate if missing)
if not os.path.exists(_DATA_PATH):
    _cwd = os.getcwd()
    try:
        os.chdir(_DIR)
        runpy.run_path("generate_data.py")
    finally:
        os.chdir(_cwd)

df = pd.read_csv(_DATA_PATH)

X = df[["rainfall", "aqi", "temperature", "peak_hour", "location_risk"]]
y = df["risk_score"]

# Train model
model = RandomForestRegressor(n_estimators=50, random_state=42)
model.fit(X, y)

def predict_risk(rainfall, aqi, temperature, peak, location_risk):
    pred = model.predict([[rainfall, aqi, temperature, int(peak), location_risk]])
    return max(0, min(round(pred[0], 2), 1.0))

feature_names = ["rainfall", "aqi", "temperature", "peak_hour", "location_risk"]

def get_feature_importance():
    importance = model.feature_importances_
    return dict(zip(feature_names, importance))