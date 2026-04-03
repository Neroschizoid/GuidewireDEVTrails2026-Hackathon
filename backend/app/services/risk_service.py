from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ml.inference import run_inference
from app.models.db_models import RiskProfileDB, WorkerDB
from app.schemas.contracts import RiskRequest, RiskResponse


def calculate_risk(payload: RiskRequest, db: Session) -> RiskResponse:
    worker = db.get(WorkerDB, payload.worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    output = run_inference(
        rainfall=payload.rainfall,
        aqi=payload.aqi,
        temperature=payload.temperature,
        peak=payload.peak,
        location_risk=payload.location_risk,
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
    return RiskResponse(
        worker_id=payload.worker_id,
        risk_score=output.risk_score,
        premium_quote=output.premium_quote,
        estimated_loss=output.estimated_loss,
        fraud_flag=output.fraud_flag,
        timestamp=now,
    )
