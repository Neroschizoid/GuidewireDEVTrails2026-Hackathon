from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
import bcrypt

from app.core.db import get_db
from app.models.db_models import WorkerDB
from app.schemas.contracts import (
    RegisterWorkerRequest, 
    RegisterWorkerResponse, 
    WorkerInfoResponse,
    LoginWorkerRequest
)

router = APIRouter()

@router.post("/workers/register", response_model=RegisterWorkerResponse)
def register_worker(payload: RegisterWorkerRequest, db: Session = Depends(get_db)) -> RegisterWorkerResponse:
    existing = db.scalar(select(WorkerDB).where(WorkerDB.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = bcrypt.hashpw(payload.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    worker = WorkerDB(
        id=str(uuid.uuid4()),
        name=payload.name,
        email=payload.email,
        hashed_password=hashed_password,
        location=payload.location,
        income=payload.income,
        active=True,
    )
    db.add(worker)
    db.commit()
    return RegisterWorkerResponse(worker_id=worker.id, location=worker.location, active=worker.active)

@router.post("/workers/login", response_model=WorkerInfoResponse)
def login_worker(payload: LoginWorkerRequest, db: Session = Depends(get_db)) -> WorkerInfoResponse:
    worker = db.scalar(select(WorkerDB).where(WorkerDB.email == payload.email))
    if not worker:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not bcrypt.checkpw(payload.password.encode('utf-8'), worker.hashed_password.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return WorkerInfoResponse(
        worker_id=worker.id,
        name=worker.name,
        email=worker.email,
        location=worker.location,
        income=worker.income,
        active=worker.active,
    )

@router.get("/workers/{worker_id}", response_model=WorkerInfoResponse)
def get_worker(worker_id: str, db: Session = Depends(get_db)) -> WorkerInfoResponse:
    worker = db.get(WorkerDB, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    return WorkerInfoResponse(
        worker_id=worker.id,
        name=worker.name,
        email=worker.email,
        location=worker.location,
        income=worker.income,
        active=worker.active,
    )
