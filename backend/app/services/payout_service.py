from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db_models import EventDB, PayoutDB, WorkerDB
from app.schemas.contracts import PayoutResult


def process_payout(worker: WorkerDB, event: EventDB, amount: float, db: Session) -> PayoutResult:
    idempotency_key = f"{worker.id}:{event.id}"
    existing = db.scalar(
        select(PayoutDB).where(PayoutDB.worker_id == worker.id, PayoutDB.event_id == event.id)
    )
    if existing is not None:
        return PayoutResult(
            payout_id=existing.id,
            worker_id=existing.worker_id,
            event_id=existing.event_id,
            amount=existing.amount,
            status="already_processed",
        )

    payout = PayoutDB(
        id=str(uuid.uuid4()),
        worker_id=worker.id,
        event_id=event.id,
        amount=round(max(amount, 0.0), 2),
        status="processed",
        idempotency_key=idempotency_key,
    )
    db.add(payout)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(PayoutDB).where(PayoutDB.worker_id == worker.id, PayoutDB.event_id == event.id)
        )
        if existing is None:
            raise
        return PayoutResult(
            payout_id=existing.id,
            worker_id=existing.worker_id,
            event_id=existing.event_id,
            amount=existing.amount,
            status="already_processed",
        )

    return PayoutResult(
        payout_id=payout.id,
        worker_id=payout.worker_id,
        event_id=payout.event_id,
        amount=payout.amount,
        status=payout.status,
    )
