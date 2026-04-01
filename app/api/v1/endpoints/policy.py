from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.contracts import PurchasePolicyRequest, PurchasePolicyResponse
from app.services.policy_service import purchase_policy


router = APIRouter()


@router.post("/policy/purchase", response_model=PurchasePolicyResponse)
def policy_purchase(payload: PurchasePolicyRequest, db: Session = Depends(get_db)) -> PurchasePolicyResponse:
    return purchase_policy(payload, db)
