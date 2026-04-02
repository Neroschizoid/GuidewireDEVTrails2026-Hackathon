from __future__ import annotations

from dataclasses import dataclass

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
) -> InferenceOutput:
    model = load_model()
    features = preprocess_features(rainfall, aqi, temperature, peak, location_risk)
    risk_score = model.predict(features)
    premium_quote = round(20.0 * (1.0 + risk_score), 2)
    estimated_loss = round(income * max(hours / 8.0, 0.0) * risk_score, 2)

    # Basic fraud heuristic for demo/testing.
    fraud_flag = income > 2000 and hours < 1 and risk_score > 0.7
    return InferenceOutput(
        risk_score=risk_score,
        premium_quote=premium_quote,
        estimated_loss=estimated_loss,
        fraud_flag=fraud_flag,
    )
