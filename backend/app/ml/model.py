import os
import joblib

DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(DIR, "model.pkl")

model = joblib.load(MODEL_PATH)

def predict_risk(rainfall, aqi, temperature, peak, location_risk):
    pred = model.predict([[
        rainfall,
        aqi,
        temperature,
        int(peak),
        location_risk
    ]])
    return max(0, min(round(pred[0], 2), 1.0))