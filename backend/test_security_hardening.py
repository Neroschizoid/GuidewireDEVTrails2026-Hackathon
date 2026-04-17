import os

import pytest
from fastapi import HTTPException
from fastapi import Response

from app.api.v1.endpoints.policy import policy_purchase
from app.api.v1.endpoints.risk import risk_calculate
from app.core.security import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    get_current_admin_worker,
    get_secret_key,
    is_admin_worker,
    set_refresh_cookie,
)
from app.models.db_models import WorkerDB
from app.schemas.contracts import PurchasePolicyRequest, RiskRequest


def _worker(worker_id: str, email: str) -> WorkerDB:
    return WorkerDB(
        id=worker_id,
        name="Test Worker",
        email=email,
        hashed_password="hashed",
        location="Bengaluru",
        income=1000.0,
        active=True,
        shield=0,
        trust_score=100.0,
    )


def test_get_secret_key_requires_env(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        get_secret_key()


def test_is_admin_worker_accepts_email_allowlist(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com,ops@example.com")

    assert is_admin_worker(_worker("worker-1", "admin@example.com")) is True
    assert is_admin_worker(_worker("worker-2", "user@example.com")) is False


def test_get_current_admin_worker_rejects_non_admin(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")

    with pytest.raises(HTTPException, match="Admin access required"):
        get_current_admin_worker(_worker("worker-2", "user@example.com"))


def test_set_refresh_cookie_marks_cookie_httponly(monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "true")
    response = Response()

    set_refresh_cookie(response, "refresh-token-value")

    set_cookie = response.headers["set-cookie"]
    assert REFRESH_COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie


def test_clear_refresh_cookie_expires_cookie(monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "false")
    response = Response()

    clear_refresh_cookie(response)

    set_cookie = response.headers["set-cookie"]
    assert REFRESH_COOKIE_NAME in set_cookie
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()


def test_risk_calculate_blocks_cross_account_access():
    payload = RiskRequest(
        worker_id="worker-2",
        lat=12.9,
        lon=77.5,
        temperature=30,
        peak=True,
        location_risk=0.4,
        hours=8,
        base_price=20,
    )

    with pytest.raises(HTTPException, match="Access denied"):
        risk_calculate(payload=payload, db=None, current_worker=_worker("worker-1", "user@example.com"))


def test_policy_purchase_blocks_cross_account_access():
    payload = PurchasePolicyRequest(worker_id="worker-2", base_price=20, days=7)

    with pytest.raises(HTTPException, match="Access denied"):
        policy_purchase(payload=payload, db=None, current_worker=_worker("worker-1", "user@example.com"))
