from fastapi import FastAPI
from model import predict_risk
from premium import calculate_premium
from loss import estimate_loss
from fraud import check_fraud
from model import get_feature_importance
app = FastAPI()

@app.get("/")
def home():
    return {"message": "ML Service Running "}

@app.get("/feature-importance")
def feature_importance():
    return get_feature_importance()

@app.post("/predict")
def predict(data: dict):
    rainfall = data.get("rainfall", 0)
    aqi = data.get("aqi", 0)
    peak = data.get("peak", False)

    income = data.get("income", 100)
    hours = data.get("hours", 1)

    is_active = data.get("active", True)
    already_paid = data.get("paid", False)

    # ML Pipeline
    temperature = data.get("temperature", 30)
    location_risk = data.get("location_risk", 0.5)
    base_price = data.get("base_price", 20)

    risk = predict_risk(rainfall, aqi, temperature, peak, location_risk)
    premium = calculate_premium(risk, base_price=base_price)
    loss = estimate_loss(income, hours)
    fraud = check_fraud(is_active, already_paid)

    return {
        "risk_score": round(risk, 2),
        "weekly_premium": round(premium, 2),
        "estimated_loss": int(loss),
        "fraud_flag": fraud
    }