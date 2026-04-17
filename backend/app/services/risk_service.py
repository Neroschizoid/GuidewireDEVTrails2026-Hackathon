from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ml.inference import run_inference
from app.models.db_models import RiskProfileDB, WorkerDB
from app.schemas.contracts import RiskRequest, RiskResponse
from app.services.analytics_service import estimate_location_risk
from app.services.weather_service import fetch_weather_snapshot, get_peak_hour


def calculate_risk(payload: RiskRequest, db: Session) -> RiskResponse:
    worker = db.get(WorkerDB, payload.worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Fetch Rainfall, AQI, and Temperature
    snapshot = fetch_weather_snapshot(payload.lat, payload.lon)
    rainfall = snapshot.current_rainfall
    aqi = snapshot.current_aqi
    temp = snapshot.current_temperature
    peak = get_peak_hour()
    forecast_rainfall = max(snapshot.next_24h_rainfall, rainfall)
    forecast_aqi = max(snapshot.next_24h_peak_aqi, aqi)
    loc_risk = estimate_location_risk(
        db=db,
        location=worker.location,
        current_rainfall=rainfall,
        current_aqi=aqi,
        forecast_rainfall=forecast_rainfall,
        forecast_aqi=forecast_aqi,
    )

    output = run_inference(
        rainfall=max(rainfall, forecast_rainfall / 4.0),
        aqi=max(aqi, forecast_aqi),
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
        rain=round(rainfall, 2),
        aqi=round(aqi, 2),
        location_risk=loc_risk,
        forecast_rainfall=round(forecast_rainfall, 2),
        forecast_aqi=round(forecast_aqi, 2),
        temperature=temp,
        peak_status=peak,
        weather_unavailable=not snapshot.available,
        weather_error=snapshot.error,
        timestamp=now,
    )
