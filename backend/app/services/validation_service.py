from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import EventDB, PayoutDB, PolicyDB, WorkerDB


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_for_payout(worker: WorkerDB, event: EventDB, db: Session) -> bool:
    if not worker.active:
        return False

    if worker.location != event.location:
        return False

    policy = db.scalar(select(PolicyDB).where(PolicyDB.worker_id == worker.id))
    if policy is None or policy.status != "active":
        return False

    now = datetime.now(timezone.utc)
    if not (_as_utc(policy.start_date) <= now <= _as_utc(policy.end_date)):
        return False

    existing = db.scalar(
        select(PayoutDB).where(PayoutDB.worker_id == worker.id, PayoutDB.event_id == event.id)
    )
    if existing is not None:
        return False

    return True


def validate_eligibility_for_payout(worker: WorkerDB, event: EventDB, db: Session) -> bool:
    """
    Eligibility check for payouts that does NOT block already-processed payouts.
    Idempotency is enforced in `process_payout` via the unique DB constraint.
    """
    if not worker.active:
        return False

    if worker.location != event.location:
        return False

    policy = db.scalar(select(PolicyDB).where(PolicyDB.worker_id == worker.id))
    if policy is None or policy.status != "active":
        return False

    now = datetime.now(timezone.utc)
    if not (_as_utc(policy.start_date) <= now <= _as_utc(policy.end_date)):
        return False

    return True
