from __future__ import annotations

import os
import random
import hmac
import hashlib
from dataclasses import dataclass
from uuid import uuid4

import httpx

from app.models.db_models import WorkerDB


PAYMENT_GATEWAYS = {
    "razorpay_test": {
        "name": "Razorpay Test Mode",
        "type": "checkout",
        "currency": "INR",
        "description": "Razorpay checkout for policy purchase.",
    },
}

PAYOUT_GATEWAYS = {
    "razorpay_test": {
        "name": "RazorpayX Test Payouts",
        "type": "payout",
        "description": "Simulated bank transfer using a RazorpayX-style payout rail.",
    },
    "stripe_sandbox": {
        "name": "Stripe Sandbox Transfers",
        "type": "payout",
        "description": "Mock transfer to a connected account or card balance.",
    },
    "upi_simulator": {
        "name": "UPI Instant Simulator",
        "type": "payout",
        "description": "Mock real-time UPI push transfer for lost wage claims.",
    },
}


@dataclass
class MockTransaction:
    gateway: str
    gateway_name: str
    reference: str
    status: str
    message: str
    beneficiary_masked: str | None = None


def _razorpay_keys() -> tuple[str | None, str | None]:
    return os.getenv("RAZORPAY_TEST_KEY_ID"), os.getenv("RAZORPAY_TEST_KEY_SECRET")


def list_gateway_catalog() -> dict[str, list[dict[str, str]]]:
    razorpay_key_id, razorpay_key_secret = _razorpay_keys()
    razorpay_configured = bool(razorpay_key_id) and bool(razorpay_key_secret)
    return {
        "payment_gateways": [
            {
                "code": code,
                **meta,
                "public_key": razorpay_key_id if code == "razorpay_test" and razorpay_configured else None,
                "is_configured": razorpay_configured if code == "razorpay_test" else True,
                "description": (
                    f"{meta['description']} {'Configured with test API keys.' if code == 'razorpay_test' and razorpay_configured else ''}".strip()
                ),
            }
            for code, meta in PAYMENT_GATEWAYS.items()
        ],
        "payout_gateways": [
            {"code": code, **meta, "is_configured": True} for code, meta in PAYOUT_GATEWAYS.items()
        ],
    }


def _require_gateway(code: str, catalog: dict[str, dict[str, str]]) -> dict[str, str]:
    gateway = catalog.get(code)
    if gateway is None:
        raise ValueError(f"Unsupported gateway: {code}")
    return gateway


def mask_beneficiary(worker: WorkerDB) -> str | None:
    if worker.bank_account_number:
        return f"****{worker.bank_account_number[-4:]}"
    return None


def simulate_policy_payment(worker: WorkerDB, gateway_code: str, amount: float) -> MockTransaction:
    gateway = _require_gateway(gateway_code, PAYMENT_GATEWAYS)
    reference = f"{gateway_code[:4].upper()}_PAY_{uuid4().hex[:10].upper()}"
    status = "captured"
    message = (
        f"{gateway['name']} approved a mock premium payment of ₹{amount:.2f} "
        f"for {worker.name}."
    )
    return MockTransaction(
        gateway=gateway_code,
        gateway_name=gateway["name"],
        reference=reference,
        status=status,
        message=message,
    )


def create_razorpay_order(amount: float, receipt: str) -> dict[str, str]:
    key_id, key_secret = _razorpay_keys()
    if not key_id or not key_secret:
        raise ValueError("Razorpay test keys are not configured")

    payload = {
        "amount": int(round(amount * 100)),
        "currency": "INR",
        "receipt": receipt[:40],
        "payment_capture": 1,
    }
    response = httpx.post(
        "https://api.razorpay.com/v1/orders",
        auth=(key_id, key_secret),
        json=payload,
        timeout=20.0,
    )
    response.raise_for_status()
    return response.json()


def verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    _key_id, key_secret = _razorpay_keys()
    if not key_secret:
        return False
    body = f"{order_id}|{payment_id}"
    expected = hmac.new(key_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def choose_payout_gateway(worker: WorkerDB) -> str:
    if worker.preferred_payout_gateway in PAYOUT_GATEWAYS:
        return str(worker.preferred_payout_gateway)
    return "upi_simulator"


def simulate_instant_payout(worker: WorkerDB, amount: float) -> MockTransaction:
    gateway_code = choose_payout_gateway(worker)
    gateway = _require_gateway(gateway_code, PAYOUT_GATEWAYS)

    if not worker.bank_account_number or not worker.bank_account_verified:
        return MockTransaction(
            gateway=gateway_code,
            gateway_name=gateway["name"],
            reference=f"{gateway_code[:4].upper()}_HOLD_{uuid4().hex[:10].upper()}",
            status="requires_bank_account",
            message="Payout is ready but bank payout details are missing or unverified.",
            beneficiary_masked=None,
        )

    reference = f"{gateway_code[:4].upper()}_OUT_{uuid4().hex[:10].upper()}"
    transfer_status = "transferred" if amount > 0 else "cancelled"
    speed = random.choice(["Instant", "Real-time", "Under 30 seconds"])
    return MockTransaction(
        gateway=gateway_code,
        gateway_name=gateway["name"],
        reference=reference,
        status=transfer_status,
        message=f"{speed} mock transfer initiated through {gateway['name']}.",
        beneficiary_masked=mask_beneficiary(worker),
    )
