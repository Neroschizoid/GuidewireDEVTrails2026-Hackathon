from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.db_models import WorkerDB
from app.schemas.contracts import RegisterWorkerRequest, RegisterWorkerResponse


router = APIRouter()


@router.post("/workers/register", response_model=RegisterWorkerResponse)
def register_worker(payload: RegisterWorkerRequest, db: Session = Depends(get_db)) -> RegisterWorkerResponse:
    worker = WorkerDB(
        id=str(uuid.uuid4()),
        name=payload.name,
        location=payload.location,
        income=payload.income,
        active=True,
    )
    db.add(worker)
    db.commit()
    return RegisterWorkerResponse(worker_id=worker.id, location=worker.location, active=worker.active)
