from __future__ import annotations

from dataclasses import dataclass
import os

import httpx

from app.ml.model_loader import load_model
from app.ml.preprocessing import preprocess_features


@dataclass
class InferenceOutput:
    risk_score: float
    premium_quote: float
    estimated_loss: float
    fraud_flag: bool


def run_inference(
    rainfall: float,
    aqi: float,
    temperature: float,
    peak: bool,
    location_risk: float,
    income: float,
    hours: float,
    active: bool = True,
    paid: bool = False,
    base_price: float = 20.0,
) -> InferenceOutput:
    ml_api_url = os.getenv("ML_API_URL")
    if ml_api_url:
        payload = {
            "rainfall": rainfall,
            "aqi": aqi,
            "peak": peak,
            "income": income,
            "hours": hours,
            "active": active,
            "paid": paid,
            "temperature": temperature,
            "location_risk": location_risk,
            "base_price": base_price,
        }
        try:
            res = httpx.post(ml_api_url, json=payload, timeout=5)
            res.raise_for_status()
            data = res.json()
            return InferenceOutput(
                risk_score=float(data["risk_score"]),
                premium_quote=float(data["weekly_premium"]),
                estimated_loss=float(data["estimated_loss"]),
                fraud_flag=bool(data["fraud_flag"]),
            )
        except Exception:
            # If ML service is down or returns unexpected payload, fall back to local model.
            pass

    model = load_model()
    features = preprocess_features(rainfall, aqi, temperature, peak, location_risk)
    risk_score = model.predict(features)
    premium_quote = round(base_price * (1.0 + risk_score), 2)
    estimated_loss = round(income * max(hours / 8.0, 0.0) * risk_score, 2)

    # Basic fraud heuristic for demo/testing.
    fraud_flag = income > 2000 and hours < 1 and risk_score > 0.7
    return InferenceOutput(
        risk_score=risk_score,
        premium_quote=premium_quote,
        estimated_loss=estimated_loss,
        fraud_flag=fraud_flag,
    )
