from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ml.inference import run_inference
from app.models.db_models import RiskProfileDB, WorkerDB
from app.schemas.contracts import RiskRequest, RiskResponse
from app.services.weather_service import fetch_live_weather, get_peak_hour


def calculate_risk(payload: RiskRequest, db: Session) -> RiskResponse:
    worker = db.get(WorkerDB, payload.worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Fetch Rainfall, AQI, and Temperature
    rainfall, aqi, temp = fetch_live_weather(payload.lat, payload.lon)
    peak = get_peak_hour()
    loc_risk = 0.6  # static as requested

    output = run_inference(
        rainfall=rainfall,
        aqi=aqi,
        temperature=temp,
        peak=bool(peak),
        location_risk=loc_risk,
        income=worker.income,
        hours=payload.hours,
        active=worker.active,
        paid=False,
        base_price=payload.base_price,
    )
    now = datetime.now(timezone.utc)
    db.merge(RiskProfileDB(
        worker_id=payload.worker_id,
        risk_score=output.risk_score,
        timestamp=now,
    ))
    db.commit()
    # recommendation logic: 0-0.44 -> Basic (1), 0.45-0.74 -> Pro (2), 0.75+ -> Elite (3)
    rec_tier = 1
    rec_name = "Basic Shield"
    if output.risk_score >= 0.75:
        rec_tier = 3
        rec_name = "Elite Armor"
    elif output.risk_score >= 0.45:
        rec_tier = 2
        rec_name = "Pro Armor"

    return RiskResponse(
        worker_id=payload.worker_id,
        risk_score=output.risk_score,
        premium_quote=output.premium_quote,
        estimated_loss=output.estimated_loss,
        fraud_flag=output.fraud_flag,
        recommended_tier=rec_tier,
        recommended_tier_name=rec_name,
        temperature=temp,
        peak_status=peak,
        timestamp=now,
    )
