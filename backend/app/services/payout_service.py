from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db_models import EventDB, PayoutDB, WorkerDB
from app.schemas.contracts import PayoutResult
from app.services.gateway_service import simulate_instant_payout


def process_payout(
    worker: WorkerDB,
    event: EventDB,
    amount: float,
    db: Session,
    fraud_score: float = 0.0,
    fraud_reason: str | None = None,
    is_flagged: bool = False
) -> PayoutResult:
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
            payout_gateway=existing.payout_gateway,
            payout_reference=existing.payout_reference,
            transfer_status=existing.transfer_status,
            beneficiary_masked=existing.beneficiary_masked,
        )

    payout_transfer = simulate_instant_payout(worker, amount)
    payout_status = "processed" if not is_flagged else "flagged_for_review"
    if payout_transfer.status == "requires_bank_account" and not is_flagged:
        payout_status = "pending_bank_details"

    payout = PayoutDB(
        id=str(uuid.uuid4()),
        worker_id=worker.id,
        event_id=event.id,
        amount=round(max(amount, 0.0), 2),
        status=payout_status,
        idempotency_key=idempotency_key,
        fraud_score=fraud_score,
        fraud_reason=fraud_reason,
        is_flagged=is_flagged,
        payout_gateway=payout_transfer.gateway,
        payout_reference=payout_transfer.reference,
        transfer_status=payout_transfer.status,
        beneficiary_masked=payout_transfer.beneficiary_masked,
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
            payout_gateway=existing.payout_gateway,
            payout_reference=existing.payout_reference,
            transfer_status=existing.transfer_status,
            beneficiary_masked=existing.beneficiary_masked,
        )

    return PayoutResult(
        payout_id=payout.id,
        worker_id=payout.worker_id,
        event_id=payout.event_id,
        amount=payout.amount,
        status=payout.status,
        fraud_score=payout.fraud_score,
        fraud_reason=payout.fraud_reason,
        is_flagged=payout.is_flagged,
        payout_gateway=payout.payout_gateway,
        payout_reference=payout.payout_reference,
        transfer_status=payout.transfer_status,
        beneficiary_masked=payout.beneficiary_masked,
    )
