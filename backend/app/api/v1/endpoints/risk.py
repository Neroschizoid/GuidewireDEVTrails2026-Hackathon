from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.contracts import RiskRequest, RiskResponse
from app.services.risk_service import calculate_risk


router = APIRouter()


@router.post("/risk/calculate", response_model=RiskResponse)
def risk_calculate(payload: RiskRequest, db: Session = Depends(get_db)) -> RiskResponse:
    return calculate_risk(payload, db)
