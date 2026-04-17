from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_worker
from app.models.db_models import EventDB, WorkerDB
from app.schemas.contracts import PayoutResult, ProcessPayoutRequest
from app.services.payout_service import process_payout
from app.services.validation_service import validate_eligibility_for_payout


router = APIRouter()


@router.post("/payout/process", response_model=PayoutResult)
def payout_process(
    payload: ProcessPayoutRequest,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker)
) -> PayoutResult:
    if current_worker.id != payload.worker_id:
        raise HTTPException(status_code=403, detail="Access denied")
    worker = current_worker
    event = db.get(EventDB, payload.event_id)
    if worker is None or event is None:
        raise HTTPException(status_code=404, detail="Worker or event not found")

    if not validate_eligibility_for_payout(worker=worker, event=event, db=db):
        raise HTTPException(status_code=400, detail="Payout not eligible (validation failed)")

        return process_payout(worker=worker, event=event, amount=payload.amount, db=db)


from typing import List
from app.schemas.contracts import PayoutHistoryItem

@router.get("/payout/history", response_model=List[PayoutHistoryItem])
def get_payout_history(
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker)
):
    from sqlalchemy.orm import joinedload
    from app.models.db_models import PayoutDB
    
    # Needs to fetch payouts for the current worker, joined with the event to get the trigger type.
    payouts = db.query(PayoutDB).join(EventDB).filter(
        PayoutDB.worker_id == current_worker.id
    ).order_by(EventDB.timestamp.desc()).all()
    
    results = []
    for p in payouts:
        # p is PayoutDB, we need to load the event or fetch the event from DB since we joined it.
        event = db.query(EventDB).filter(EventDB.id == p.event_id).first()
        if event:
            results.append(PayoutHistoryItem(
                payout_id=p.id,
                event_id=p.event_id,
                amount=p.amount,
                status=p.status,
                is_flagged=p.is_flagged,
                trigger_type=event.type,
                timestamp=event.timestamp,
                idempotency_key=p.idempotency_key,
                payout_gateway=p.payout_gateway,
                payout_reference=p.payout_reference,
                transfer_status=p.transfer_status,
                beneficiary_masked=p.beneficiary_masked,
            ))
    return results
