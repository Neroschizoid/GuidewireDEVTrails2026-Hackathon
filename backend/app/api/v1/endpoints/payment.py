from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.db import get_db
from app.core.security import get_current_worker
from app.models.db_models import WorkerDB, PolicyDB
from app.schemas.contracts import PaymentRequest, PaymentResponse

router = APIRouter()

@router.post("/payment/process", response_model=PaymentResponse)
def process_payment(
    payload: PaymentRequest,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker)
) -> PaymentResponse:
    if current_worker.id != payload.worker_id:
        raise HTTPException(status_code=403, detail="Access denied")
    worker = current_worker
        
    # Mock Payment Engine Check
    # For demo purposes, we will return True indicating a successful charge.
    payment_successful = True 
    
    if payment_successful:
        worker.shield = payload.p_id
        db.add(worker)
        
        # When purchasing a shield tier, immediately create or update a 7-day Policy contract.
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=payload.days)
        
        existing_policy = db.scalar(select(PolicyDB).where(PolicyDB.worker_id == payload.worker_id))
        
        if existing_policy:
            existing_policy.start_date = now
            existing_policy.end_date = end_date
            existing_policy.status = "active"
            existing_policy.risk_score = payload.risk_score
            existing_policy.premium = payload.premium
            db.add(existing_policy)
        else:
            new_policy = PolicyDB(
                id=str(uuid.uuid4()),
                worker_id=payload.worker_id,
                risk_score=payload.risk_score,
                premium=payload.premium,
                start_date=now,
                end_date=end_date,
                status="active",
            )
            db.add(new_policy)
            
        db.commit()
    
    return PaymentResponse(status=payment_successful)
