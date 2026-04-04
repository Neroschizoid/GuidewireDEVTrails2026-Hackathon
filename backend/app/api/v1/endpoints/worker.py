from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
import bcrypt
import jwt

from app.core.db import get_db
from app.core.security import (
    create_access_token, create_refresh_token,
    get_current_worker, SECRET_KEY, ALGORITHM
)
from app.models.db_models import WorkerDB, PolicyDB, PayoutDB, EventDB
from app.schemas.contracts import (
    RegisterWorkerRequest,
    RegisterWorkerResponse,
    WorkerInfoResponse,
    LoginWorkerRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
)

router = APIRouter()


def get_worker_stats(worker_id: str, db: Session):
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    policy = db.scalar(select(PolicyDB).where(PolicyDB.worker_id == worker_id))
    active_policy = False
    if policy and policy.status == "active":
        p_start = policy.start_date if policy.start_date.tzinfo else policy.start_date.replace(tzinfo=timezone.utc)
        p_end = policy.end_date if policy.end_date.tzinfo else policy.end_date.replace(tzinfo=timezone.utc)
        if p_start <= now <= p_end:
            active_policy = True

    result = db.execute(
        select(func.sum(PayoutDB.amount))
        .join(EventDB, PayoutDB.event_id == EventDB.id)
        .where(
            PayoutDB.worker_id == worker_id,
            EventDB.timestamp >= seven_days_ago
        )
    ).scalar_one_or_none()

    weekly_earnings = float(result) if result is not None else 0.0
    return active_policy, weekly_earnings


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

    return RegisterWorkerResponse(
        worker_id=worker.id,
        location=worker.location,
        active=worker.active,
        shield=worker.shield,
        weekly_earnings=0.0,
        active_policy=False,
        access_token=create_access_token(worker.id),
        refresh_token=create_refresh_token(worker.id),
    )


@router.post("/workers/login", response_model=WorkerInfoResponse)
def login_worker(payload: LoginWorkerRequest, db: Session = Depends(get_db)) -> WorkerInfoResponse:
    worker = db.scalar(select(WorkerDB).where(WorkerDB.email == payload.email))
    if not worker:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not bcrypt.checkpw(payload.password.encode('utf-8'), worker.hashed_password.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    active_policy, weekly_earnings = get_worker_stats(worker.id, db)

    return WorkerInfoResponse(
        worker_id=worker.id,
        name=worker.name,
        email=worker.email,
        location=worker.location,
        income=worker.income,
        active=worker.active,
        shield=worker.shield,
        weekly_earnings=weekly_earnings,
        active_policy=active_policy,
        access_token=create_access_token(worker.id),
        refresh_token=create_refresh_token(worker.id),
    )


@router.post("/workers/refresh", response_model=RefreshTokenResponse)
def refresh_access_token(payload: RefreshTokenRequest) -> RefreshTokenResponse:
    try:
        decoded = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        worker_id: str = decoded.get("sub")
        token_type: str = decoded.get("type")
        if worker_id is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired, please login again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return RefreshTokenResponse(access_token=create_access_token(worker_id))


@router.get("/workers/{worker_id}", response_model=WorkerInfoResponse)
def get_worker(
    worker_id: str,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker)
) -> WorkerInfoResponse:
    if current_worker.id != worker_id:
        raise HTTPException(status_code=403, detail="Access denied")
    worker = db.get(WorkerDB, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    active_policy, weekly_earnings = get_worker_stats(worker.id, db)

    return WorkerInfoResponse(
        worker_id=worker.id,
        name=worker.name,
        email=worker.email,
        location=worker.location,
        income=worker.income,
        active=worker.active,
        shield=worker.shield,
        weekly_earnings=weekly_earnings,
        active_policy=active_policy,
        access_token="",
        refresh_token="",
    )
