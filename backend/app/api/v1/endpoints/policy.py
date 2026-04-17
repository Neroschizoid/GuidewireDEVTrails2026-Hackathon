from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_worker
from app.models.db_models import WorkerDB
from app.schemas.contracts import PurchasePolicyRequest, PurchasePolicyResponse
from app.services.policy_service import purchase_policy


router = APIRouter()


@router.post("/policy/purchase", response_model=PurchasePolicyResponse)
def policy_purchase(
    payload: PurchasePolicyRequest,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker),
) -> PurchasePolicyResponse:
    if current_worker.id != payload.worker_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return purchase_policy(payload, db)
