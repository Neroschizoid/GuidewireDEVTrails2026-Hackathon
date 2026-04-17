from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import delete, select, func
import bcrypt
import jwt

from app.core.db import get_db
from app.core.security import (
    create_access_token, create_refresh_token,
    get_current_worker, get_secret_key, ALGORITHM,
    REFRESH_COOKIE_NAME, build_totp_uri, clear_refresh_cookie, generate_totp_secret,
    set_refresh_cookie, verify_totp_code,
)
from app.models.db_models import EventDB, PolicyDB, PayoutDB, RiskProfileDB, TriggerStateDB, WorkerDB, WorkerSessionDB
from app.schemas.contracts import (
    BankAccountRequest,
    BankAccountResponse,
    DeleteAccountResponse,
    RegisterWorkerRequest,
    RegisterWorkerResponse,
    LoginWorkerRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TwoFactorSetupResponse,
    TwoFactorStatusResponse,
    TwoFactorVerifyRequest,
    WorkerInfoResponse,
)

router = APIRouter()


def _mask_account_number(account_number: str | None) -> str | None:
    if not account_number:
        return None
    suffix = account_number[-4:]
    return f"****{suffix}"


def get_worker_stats(worker_id: str, db: Session):
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    policy = db.scalar(select(PolicyDB).where(PolicyDB.worker_id == worker_id))
    active_policy = False
    policy_start_date = None
    policy_end_date = None
    if policy and policy.status == "active":
        p_start = policy.start_date if policy.start_date.tzinfo else policy.start_date.replace(tzinfo=timezone.utc)
        p_end = policy.end_date if policy.end_date.tzinfo else policy.end_date.replace(tzinfo=timezone.utc)
        policy_start_date = p_start
        policy_end_date = p_end
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
    return active_policy, weekly_earnings, policy_start_date, policy_end_date


@router.post("/workers/register", response_model=RegisterWorkerResponse)
def register_worker(
    payload: RegisterWorkerRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> RegisterWorkerResponse:
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

    refresh_token = create_refresh_token(worker.id)
    set_refresh_cookie(response, refresh_token)

    return RegisterWorkerResponse(
        worker_id=worker.id,
        location=worker.location,
        active=worker.active,
        shield=worker.shield,
        weekly_earnings=0.0,
        active_policy=False,
        policy_start_date=None,
        policy_end_date=None,
        access_token=create_access_token(worker.id),
        refresh_token="",
        trust_score=worker.trust_score,
        two_factor_enabled=worker.two_factor_enabled,
        bank_account_linked=bool(worker.bank_account_number),
        bank_account_masked=_mask_account_number(worker.bank_account_number),
        bank_name=worker.bank_name,
        bank_account_holder=worker.bank_account_holder,
        preferred_payout_gateway=worker.preferred_payout_gateway,
    )


@router.post("/workers/login", response_model=WorkerInfoResponse)
def login_worker(
    payload: LoginWorkerRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> WorkerInfoResponse:
    worker = db.scalar(select(WorkerDB).where(WorkerDB.email == payload.email))
    if not worker:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not bcrypt.checkpw(payload.password.encode('utf-8'), worker.hashed_password.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if worker.two_factor_enabled:
        if not payload.otp_code:
            raise HTTPException(status_code=401, detail="Two-factor code is required")
        if not worker.two_factor_secret or not verify_totp_code(worker.two_factor_secret, payload.otp_code):
            raise HTTPException(status_code=401, detail="Invalid two-factor code")

    active_policy, weekly_earnings, policy_start_date, policy_end_date = get_worker_stats(worker.id, db)
    refresh_token = create_refresh_token(worker.id)
    set_refresh_cookie(response, refresh_token)

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
        policy_start_date=policy_start_date,
        policy_end_date=policy_end_date,
        access_token=create_access_token(worker.id),
        refresh_token="",
        trust_score=worker.trust_score,
        two_factor_enabled=worker.two_factor_enabled,
        bank_account_linked=bool(worker.bank_account_number),
        bank_account_masked=_mask_account_number(worker.bank_account_number),
        bank_name=worker.bank_name,
        bank_account_holder=worker.bank_account_holder,
        preferred_payout_gateway=worker.preferred_payout_gateway,
    )


@router.post("/workers/refresh", response_model=RefreshTokenResponse)
def refresh_access_token(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = Body(default=None),
) -> RefreshTokenResponse:
    refresh_token = None
    if payload is not None:
        refresh_token = payload.refresh_token
    if not refresh_token:
        refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        decoded = jwt.decode(refresh_token, get_secret_key(), algorithms=[ALGORITHM])
        worker_id: str = decoded.get("sub")
        token_type: str = decoded.get("type")
        if worker_id is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired, please login again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    set_refresh_cookie(response, create_refresh_token(worker_id))
    return RefreshTokenResponse(access_token=create_access_token(worker_id))


@router.post("/workers/logout")
def logout_worker(response: Response) -> dict[str, str]:
    clear_refresh_cookie(response)
    return {"message": "Logged out"}


@router.delete("/workers/me", response_model=DeleteAccountResponse)
def delete_worker_account(
    response: Response,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker),
) -> DeleteAccountResponse:
    worker_id = current_worker.id
    session_ids = db.scalars(
        select(WorkerSessionDB.id).where(WorkerSessionDB.worker_id == worker_id)
    ).all()

    if session_ids:
        db.execute(delete(TriggerStateDB).where(TriggerStateDB.session_id.in_(session_ids)))

    db.execute(delete(PayoutDB).where(PayoutDB.worker_id == worker_id))
    db.execute(delete(PolicyDB).where(PolicyDB.worker_id == worker_id))
    db.execute(delete(RiskProfileDB).where(RiskProfileDB.worker_id == worker_id))
    db.execute(delete(WorkerSessionDB).where(WorkerSessionDB.worker_id == worker_id))
    db.delete(current_worker)
    db.commit()

    clear_refresh_cookie(response)
    return DeleteAccountResponse(
        deleted=True,
        worker_id=worker_id,
        message="Account and related records deleted successfully",
    )


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

    active_policy, weekly_earnings, policy_start_date, policy_end_date = get_worker_stats(worker.id, db)

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
        policy_start_date=policy_start_date,
        policy_end_date=policy_end_date,
        access_token="",
        refresh_token="",
        trust_score=worker.trust_score,
        two_factor_enabled=worker.two_factor_enabled,
        bank_account_linked=bool(worker.bank_account_number),
        bank_account_masked=_mask_account_number(worker.bank_account_number),
        bank_name=worker.bank_name,
        bank_account_holder=worker.bank_account_holder,
        preferred_payout_gateway=worker.preferred_payout_gateway,
    )


@router.post("/workers/2fa/setup", response_model=TwoFactorSetupResponse)
def setup_two_factor(
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker),
) -> TwoFactorSetupResponse:
    secret = generate_totp_secret()
    current_worker.two_factor_secret = secret
    current_worker.two_factor_enabled = False
    db.add(current_worker)
    db.commit()
    return TwoFactorSetupResponse(
        secret=secret,
        otp_auth_url=build_totp_uri(secret, current_worker.email),
        manual_entry_key=secret,
    )


@router.post("/workers/2fa/enable", response_model=TwoFactorStatusResponse)
def enable_two_factor(
    payload: TwoFactorVerifyRequest,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker),
) -> TwoFactorStatusResponse:
    if not current_worker.two_factor_secret:
        raise HTTPException(status_code=400, detail="Two-factor setup has not been started")
    if not verify_totp_code(current_worker.two_factor_secret, payload.otp_code):
        raise HTTPException(status_code=400, detail="Invalid authenticator code")

    current_worker.two_factor_enabled = True
    db.add(current_worker)
    db.commit()
    return TwoFactorStatusResponse(enabled=True, message="Two-factor authentication enabled")


@router.post("/workers/2fa/disable", response_model=TwoFactorStatusResponse)
def disable_two_factor(
    payload: TwoFactorVerifyRequest,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker),
) -> TwoFactorStatusResponse:
    if not current_worker.two_factor_enabled or not current_worker.two_factor_secret:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")
    if not verify_totp_code(current_worker.two_factor_secret, payload.otp_code):
        raise HTTPException(status_code=400, detail="Invalid authenticator code")

    current_worker.two_factor_enabled = False
    current_worker.two_factor_secret = None
    db.add(current_worker)
    db.commit()
    return TwoFactorStatusResponse(enabled=False, message="Two-factor authentication disabled")


@router.post("/workers/bank-account", response_model=BankAccountResponse)
def upsert_bank_account(
    payload: BankAccountRequest,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker),
) -> BankAccountResponse:
    normalized_number = "".join(ch for ch in payload.account_number if ch.isdigit())
    normalized_ifsc = payload.ifsc.strip().upper()
    if len(normalized_number) < 8:
        raise HTTPException(status_code=400, detail="Account number must contain at least 8 digits")
    if len(normalized_ifsc) < 8:
        raise HTTPException(status_code=400, detail="IFSC code looks incomplete")

    current_worker.bank_account_holder = payload.account_holder.strip()
    current_worker.bank_name = payload.bank_name.strip()
    current_worker.bank_account_number = normalized_number
    current_worker.bank_ifsc = normalized_ifsc
    current_worker.bank_account_verified = True
    current_worker.preferred_payout_gateway = payload.preferred_payout_gateway
    db.add(current_worker)
    db.commit()

    return BankAccountResponse(
        linked=True,
        verified=True,
        account_holder=current_worker.bank_account_holder,
        bank_name=current_worker.bank_name,
        account_masked=_mask_account_number(current_worker.bank_account_number),
        ifsc=current_worker.bank_ifsc,
        preferred_payout_gateway=current_worker.preferred_payout_gateway,
        message="Bank account linked successfully",
    )


@router.get("/workers/bank-account", response_model=BankAccountResponse)
def get_bank_account(
    current_worker: WorkerDB = Depends(get_current_worker),
) -> BankAccountResponse:
    linked = bool(current_worker.bank_account_number)
    return BankAccountResponse(
        linked=linked,
        verified=bool(current_worker.bank_account_verified),
        account_holder=current_worker.bank_account_holder,
        bank_name=current_worker.bank_name,
        account_masked=_mask_account_number(current_worker.bank_account_number),
        ifsc=current_worker.bank_ifsc,
        preferred_payout_gateway=current_worker.preferred_payout_gateway,
        message="Bank account loaded" if linked else "No bank account linked",
    )
