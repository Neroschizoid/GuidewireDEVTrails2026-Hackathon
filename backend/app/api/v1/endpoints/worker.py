from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.db_models import WorkerDB
from app.schemas.contracts import RegisterWorkerRequest, RegisterWorkerResponse, WorkerInfoResponse


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


@router.get("/workers/{worker_id}", response_model=WorkerInfoResponse)
def get_worker(worker_id: str, db: Session = Depends(get_db)) -> WorkerInfoResponse:
    worker = db.get(WorkerDB, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    return WorkerInfoResponse(
        worker_id=worker.id,
        name=worker.name,
        location=worker.location,
        income=worker.income,
        active=worker.active,
    )
