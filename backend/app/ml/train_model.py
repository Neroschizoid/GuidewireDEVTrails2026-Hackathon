import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
import os

DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(DIR, "data.csv")
MODEL_PATH = os.path.join(DIR, "model.pkl")

df = pd.read_csv(DATA_PATH)

X = df[["rainfall", "aqi", "temperature", "peak_hour", "location_risk"]]
y = df["risk_score"]

model = RandomForestRegressor(n_estimators=50, random_state=42)
model.fit(X, y)

joblib.dump(model, MODEL_PATH)

print("✅ Model saved at:", MODEL_PATH)