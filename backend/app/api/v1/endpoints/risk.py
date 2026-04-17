from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_worker
from app.models.db_models import WorkerDB
from app.schemas.contracts import RiskRequest, RiskResponse
from app.services.risk_service import calculate_risk


router = APIRouter()


@router.post("/risk/calculate", response_model=RiskResponse)
def risk_calculate(
    payload: RiskRequest,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker)
) -> RiskResponse:
    if current_worker.id != payload.worker_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return calculate_risk(payload, db)
