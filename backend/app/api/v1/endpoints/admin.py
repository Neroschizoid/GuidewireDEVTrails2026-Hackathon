from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.db import get_db
from app.core.security import get_current_admin_worker
from app.models.db_models import EventDB, PayoutDB, PolicyDB, WorkerDB
from app.services.analytics_service import build_admin_forecast, build_admin_stats

router = APIRouter(dependencies=[Depends(get_current_admin_worker)])

class FlaggedClaimResponse(BaseModel):
    payout_id: str
    worker_id: str
    worker_name: str
    event_id: str
    amount: float
    fraud_score: float
    fraud_reason: Optional[str] = None

@router.get("/flagged_claims", response_model=List[FlaggedClaimResponse])
def get_flagged_claims(db: Session = Depends(get_db)):
    flagged = db.query(PayoutDB, WorkerDB).join(WorkerDB, PayoutDB.worker_id == WorkerDB.id).filter(PayoutDB.is_flagged == True).all()
    results = []
    for payout, worker in flagged:
        results.append(FlaggedClaimResponse(
            payout_id=payout.id,
            worker_id=worker.id,
            worker_name=worker.name,
            event_id=payout.event_id,
            amount=payout.amount,
            fraud_score=payout.fraud_score,
            fraud_reason=payout.fraud_reason
        ))
    return results

@router.post("/resolve_claim/{payout_id}")
def resolve_claim(payout_id: str, db: Session = Depends(get_db)):
    payout = db.query(PayoutDB).filter(PayoutDB.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    
    payout.is_flagged = False
    payout.status = "processed manually"
    db.commit()
    return {"message": "Claim resolved successfully"}

class StatsResponse(BaseModel):
    total_workers_protected: int
    active_weekly_coverage: int
    protected_earnings_estimate: float
    claims_premium_ratio: float
    loss_ratio_percent: float
    fraud_savings: float
    avg_payout_time: str
    predicted_next_week_claims: int
    predicted_next_week_loss: float
    highest_risk_day: Optional[str] = None
    forecast_location: Optional[str] = None
    weather_unavailable: bool = False

@router.get("/stats", response_model=StatsResponse)
def get_admin_stats(db: Session = Depends(get_db)):
    snapshot = build_admin_stats(db=db)
    return StatsResponse(
        total_workers_protected=snapshot.total_workers_protected,
        active_weekly_coverage=snapshot.active_weekly_coverage,
        protected_earnings_estimate=snapshot.protected_earnings_estimate,
        claims_premium_ratio=snapshot.claims_premium_ratio,
        loss_ratio_percent=snapshot.loss_ratio_percent,
        fraud_savings=snapshot.fraud_savings,
        avg_payout_time=snapshot.avg_payout_time,
        predicted_next_week_claims=snapshot.predicted_next_week_claims,
        predicted_next_week_loss=snapshot.predicted_next_week_loss,
        highest_risk_day=snapshot.highest_risk_day,
        forecast_location=snapshot.forecast_location,
        weather_unavailable=snapshot.weather_unavailable,
    )

class ForecastRequest(BaseModel):
    threshold: float
    location: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

class ForecastResponsePoint(BaseModel):
    day: str
    expected_loss: float
    workers_at_risk: int
    rainfall: float
    aqi: float
    location: str

@router.post("/forecast", response_model=List[ForecastResponsePoint])
def get_forecast(payload: ForecastRequest, db: Session = Depends(get_db)):
    results = build_admin_forecast(
        db=db,
        threshold=payload.threshold,
        location=payload.location,
        lat=payload.lat,
        lon=payload.lon,
    )
    return [ForecastResponsePoint(**item) for item in results]

class BulkResolveRequest(BaseModel):
    payout_ids: List[str]

@router.post("/bulk_resolve")
def bulk_resolve(payload: BulkResolveRequest, db: Session = Depends(get_db)):
    payouts = db.query(PayoutDB).filter(PayoutDB.id.in_(payload.payout_ids), PayoutDB.is_flagged == True).all()
    for p in payouts:
        p.is_flagged = False
        p.status = "processed manually"
    db.commit()
    return {"message": f"Successfully resolved {len(payouts)} claims.", "count": len(payouts)}

class LiveClaimItem(BaseModel):
    payout_id: str
    worker_id: str
    amount: float
    status: str
    timestamp: str

@router.get("/live_claims", response_model=List[LiveClaimItem])
def get_live_claims(db: Session = Depends(get_db)):
    payouts = db.query(PayoutDB, EventDB).join(EventDB, PayoutDB.event_id == EventDB.id)\
        .filter(PayoutDB.is_flagged == False)\
        .order_by(EventDB.timestamp.desc())\
        .limit(50).all()
    
    results = []
    for p, e in payouts:
        results.append(LiveClaimItem(
            payout_id=p.id,
            worker_id=p.worker_id,
            amount=p.amount,
            status=p.status,
            timestamp=e.timestamp.isoformat() if e.timestamp else ""
        ))
    return results
