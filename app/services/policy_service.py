from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import PolicyDB, RiskProfileDB, WorkerDB
from app.schemas.contracts import PurchasePolicyRequest, PurchasePolicyResponse


def purchase_policy(payload: PurchasePolicyRequest, db: Session) -> PurchasePolicyResponse:
    worker = db.get(WorkerDB, payload.worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    risk = db.get(RiskProfileDB, payload.worker_id)
    if risk is None:
        raise HTTPException(status_code=400, detail="Risk profile missing")

    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=payload.days)
    premium = round(payload.base_price * (1.0 + risk.risk_score), 2)

    existing = db.scalar(select(PolicyDB).where(PolicyDB.worker_id == payload.worker_id))
    if existing is not None:
        db.delete(existing)
        db.flush()

    policy = PolicyDB(
        id=str(uuid.uuid4()),
        worker_id=payload.worker_id,
        risk_score=risk.risk_score,
        premium=premium,
        start_date=start_date,
        end_date=end_date,
        status="active",
    )
    db.add(policy)
    db.commit()
    return PurchasePolicyResponse(
        policy_id=policy.id,
        worker_id=policy.worker_id,
        premium=policy.premium,
        start_date=policy.start_date,
        end_date=policy.end_date,
        status=policy.status,
    )
