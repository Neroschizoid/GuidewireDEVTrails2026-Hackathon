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
