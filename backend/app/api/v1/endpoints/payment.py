from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.db import get_db
from app.core.security import get_current_worker
from app.models.db_models import WorkerDB, PolicyDB, ShieldTierDB
from app.schemas.contracts import (
    CreatePaymentSessionRequest,
    GatewayCatalogResponse,
    GatewayOption,
    PaymentRequest,
    PaymentResponse,
    PaymentSessionResponse,
)
from app.services.gateway_service import (
    create_razorpay_order,
    list_gateway_catalog,
    simulate_policy_payment,
    verify_razorpay_signature,
)

router = APIRouter()


@router.get("/payment/gateways", response_model=GatewayCatalogResponse)
def get_gateway_catalog() -> GatewayCatalogResponse:
    catalog = list_gateway_catalog()
    return GatewayCatalogResponse(
        payment_gateways=[GatewayOption(**item) for item in catalog["payment_gateways"]],
        payout_gateways=[GatewayOption(**item) for item in catalog["payout_gateways"]],
    )


@router.post("/payment/create-session", response_model=PaymentSessionResponse)
def create_payment_session(
    payload: CreatePaymentSessionRequest,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker),
) -> PaymentSessionResponse:
    if current_worker.id != payload.worker_id:
        raise HTTPException(status_code=403, detail="Access denied")

    shield = db.get(ShieldTierDB, payload.p_id)
    if shield is None:
        raise HTTPException(status_code=400, detail="Invalid shield tier")
    if payload.premium <= 0:
        raise HTTPException(status_code=400, detail="Premium must be greater than zero")

    catalog = list_gateway_catalog()
    payment_gateway = next((item for item in catalog["payment_gateways"] if item["code"] == payload.payment_gateway), None)
    if payment_gateway is None:
        raise HTTPException(status_code=400, detail="Unsupported payment gateway")

    if payload.payment_gateway == "razorpay_test":
        if not payment_gateway.get("is_configured"):
            raise HTTPException(status_code=400, detail="Razorpay test gateway is not configured")
        try:
            receipt = f"{current_worker.id[:8]}-{payload.p_id}-{uuid.uuid4().hex[:8]}"
            order = create_razorpay_order(payload.premium, receipt)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Unable to create Razorpay order: {exc}") from exc

        return PaymentSessionResponse(
            gateway=payload.payment_gateway,
            key_id=payment_gateway.get("public_key"),
            order_id=order.get("id"),
            amount=payload.premium,
            currency=order.get("currency", "INR"),
            description=f"{shield.name} coverage for {payload.days} days",
            worker_name=current_worker.name,
            worker_email=current_worker.email,
        )

    return PaymentSessionResponse(
        gateway=payload.payment_gateway,
        key_id=payment_gateway.get("public_key"),
        order_id=f"mock_order_{uuid.uuid4().hex[:10]}",
        amount=payload.premium,
        currency=str(payment_gateway.get("currency") or "INR"),
        description=f"{shield.name} coverage for {payload.days} days",
        worker_name=current_worker.name,
        worker_email=current_worker.email,
    )

@router.post("/payment/process", response_model=PaymentResponse)
def process_payment(
    payload: PaymentRequest,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker)
) -> PaymentResponse:
    if current_worker.id != payload.worker_id:
        raise HTTPException(status_code=403, detail="Access denied")
    worker = current_worker

    shield = db.get(ShieldTierDB, payload.p_id)
    if shield is None:
        raise HTTPException(status_code=400, detail="Invalid shield tier")

    if payload.days <= 0:
        raise HTTPException(status_code=400, detail="Policy duration must be greater than zero")

    if payload.p_id > 0 and payload.premium <= 0:
        raise HTTPException(status_code=400, detail="Premium must be greater than zero for paid shields")

    if payload.payment_gateway == "razorpay_test":
        if not payload.payment_reference or not payload.payment_order_id or not payload.payment_signature:
            raise HTTPException(status_code=400, detail="Razorpay payment details are incomplete")
        if not verify_razorpay_signature(payload.payment_order_id, payload.payment_reference, payload.payment_signature):
            raise HTTPException(status_code=400, detail="Razorpay payment signature verification failed")
        payment_reference = payload.payment_reference
        payment_status = payload.payment_status or "captured"
        payment_message = f"Razorpay payment {payment_reference} verified successfully."
    else:
        payment_tx = simulate_policy_payment(worker, payload.payment_gateway, payload.premium)
        payment_reference = payment_tx.reference
        payment_status = payment_tx.status
        payment_message = payment_tx.message

    worker.shield = payload.p_id
    db.add(worker)

    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=payload.days)

    existing_policy = db.scalar(select(PolicyDB).where(PolicyDB.worker_id == payload.worker_id))

    if existing_policy:
        existing_policy.start_date = now
        existing_policy.end_date = end_date
        existing_policy.status = "active"
        existing_policy.risk_score = payload.risk_score
        existing_policy.premium = payload.premium
        existing_policy.payment_gateway = payload.payment_gateway
        existing_policy.payment_reference = payment_reference
        existing_policy.payment_status = payment_status
        db.add(existing_policy)
        policy = existing_policy
    else:
        policy = PolicyDB(
            id=str(uuid.uuid4()),
            worker_id=payload.worker_id,
            risk_score=payload.risk_score,
            premium=payload.premium,
            start_date=now,
            end_date=end_date,
            status="active",
            payment_gateway=payload.payment_gateway,
            payment_reference=payment_reference,
            payment_status=payment_status,
        )
        db.add(policy)

    db.commit()

    return PaymentResponse(
        status=True,
        policy_id=policy.id,
        premium=policy.premium,
        start_date=policy.start_date,
        end_date=policy.end_date,
        shield_id=worker.shield,
        payment_gateway=policy.payment_gateway,
        payment_reference=policy.payment_reference,
        payment_status=policy.payment_status,
        message=f"Coverage activated. {payment_message}",
    )
