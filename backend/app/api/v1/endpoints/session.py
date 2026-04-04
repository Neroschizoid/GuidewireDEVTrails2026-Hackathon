from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_worker
from app.models.db_models import TriggerStateDB, WorkerDB, WorkerSessionDB
from app.schemas.contracts import SessionEndResponse, SessionStartRequest, SessionStartResponse

router = APIRouter()

TRIGGER_TYPES = ["rain", "aqi"]


@router.post("/session/start", response_model=SessionStartResponse)
def start_session(
    payload: SessionStartRequest,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker),
) -> SessionStartResponse:
    """
    Begin a new tracking session for the authenticated worker.
    Seeds trigger_state rows (one per trigger type) so the idempotency
    state machine is ready before the first /check-triggers poll.
    """
    # End any lingering active sessions first
    existing = db.scalars(
        select(WorkerSessionDB).where(
            WorkerSessionDB.worker_id == current_worker.id,
            WorkerSessionDB.status == "active",
        )
    ).all()
    for s in existing:
        s.status = "ended"
        s.ended_at = datetime.now(timezone.utc)
    db.flush()

    now = datetime.now(timezone.utc)
    session = WorkerSessionDB(
        id=str(uuid.uuid4()),
        worker_id=current_worker.id,
        started_at=now,
        status="active",
    )
    db.add(session)
    db.flush()

    # Seed trigger_state rows with active=False for each trigger type
    for t_type in TRIGGER_TYPES:
        db.add(TriggerStateDB(
            id=str(uuid.uuid4()),
            session_id=session.id,
            trigger_type=t_type,
            active=False,
            last_triggered_at=None,
        ))

    db.commit()
    return SessionStartResponse(session_id=session.id, started_at=now)


@router.post("/session/end", response_model=SessionEndResponse)
def end_session(
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker),
) -> SessionEndResponse:
    """
    End the worker's active session and halt trigger eligibility.
    """
    session = db.scalar(
        select(WorkerSessionDB).where(
            WorkerSessionDB.worker_id == current_worker.id,
            WorkerSessionDB.status == "active",
        )
    )
    if session is None:
        raise HTTPException(status_code=404, detail="No active session found")

    now = datetime.now(timezone.utc)
    session.status = "ended"
    session.ended_at = now
    db.commit()

    return SessionEndResponse(session_id=session.id, ended_at=now)
