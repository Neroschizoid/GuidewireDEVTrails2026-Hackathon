"""
Supabase Integration Tests
==========================
These tests verify that every API endpoint correctly reads from and writes
to the real Supabase PostgreSQL database.

They run against the actual DB defined in backend/.env (DATABASE_URL).
Each test creates its own isolated worker / data and cleans up afterwards,
so running them multiple times is safe.

Run with:
    cd backend
    pytest tests/test_supabase_integration.py -v
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Bootstrap: load the real DATABASE_URL from .env BEFORE any app import
# ---------------------------------------------------------------------------
import os
from pathlib import Path
from dotenv import load_dotenv

# Look for .env next to this tests/ folder (i.e., backend/.env)
_env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

_db_url = os.getenv("DATABASE_URL", "")
if not _db_url or "[YOUR-PASSWORD]" in _db_url:
    pytest.exit(
        "DATABASE_URL is not configured. "
        "Add your Supabase connection string to backend/.env and retry.",
        returncode=1,
    )

# Normalise postgres:// → postgresql:// for SQLAlchemy
if _db_url.startswith("postgres://"):
    os.environ["DATABASE_URL"] = _db_url.replace("postgres://", "postgresql://", 1)

# ---------------------------------------------------------------------------
# App + helper imports (must come AFTER env is set)
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import Base, engine  # noqa: E402
from app.main import app              # noqa: E402

client = TestClient(app, raise_server_exceptions=True)

# MOCK Weather API for testing different test conditions based on 'lat'
def mock_weather(lat, lon):
    if lat == 90.0: return 90.0, 200.0
    if lat == 10.0: return 10.0, 350.0
    if lat == 0.0: return 10.0, 50.0
    return 80.0, 250.0

import app.services.event_service
import app.services.risk_service
app.services.event_service.fetch_live_weather = mock_weather
app.services.risk_service.fetch_live_weather = mock_weather



# ---------------------------------------------------------------------------
# Session-scoped fixture: ensure all tables exist in Supabase once per run
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def ensure_tables():
    """Create tables if they don't exist yet. Never drops — safe on real DB."""
    Base.metadata.create_all(bind=engine)
    yield


# ---------------------------------------------------------------------------
# Helper: unique location per test so workers don't bleed into each other
# ---------------------------------------------------------------------------
def _loc() -> str:
    return f"test-zone-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# 1. Health / DB connectivity
# ---------------------------------------------------------------------------
class TestHealth:
    def test_root_health(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_db_connectivity(self):
        """The /test-db endpoint does SELECT 1 against Supabase."""
        r = client.get("/test-db")
        assert r.status_code == 200, r.text
        assert r.json()["result"] == 1


# ---------------------------------------------------------------------------
# 2. Worker registration & retrieval
# ---------------------------------------------------------------------------
class TestWorker:

    def test_login_worker(self):
        email = f"login_{uuid.uuid4().hex[:8]}@example.com"
        r = client.post(
            "/api/v1/workers/register",
            json={"name": "Login Test", "email": email, "password": "mysecret", "location": _loc(), "income": 1200},
        )
        assert r.status_code == 200
        
        login = client.post(
            "/api/v1/workers/login",
            json={"email": email, "password": "mysecret"}
        )
        assert login.status_code == 200
        assert login.json()["email"] == email

    def test_register_worker(self):
        r = client.post(
            "/api/v1/workers/register",
            json={"email": f"test_{uuid.uuid4().hex[:8]}@test.com", "password": "secure123", "name": "Integration Test Worker", "location": _loc(), "income": 1500},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "worker_id" in body
        assert body["active"] is True

    def test_get_worker_after_register(self):
        loc = _loc()
        reg = client.post(
            "/api/v1/workers/register",
            json={"email": f"test_{uuid.uuid4().hex[:8]}@test.com", "password": "secure123", "name": "Fetch Test Worker", "location": loc, "income": 900},
        )
        wid = reg.json()["worker_id"]

        r = client.get(f"/api/v1/workers/{wid}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["worker_id"] == wid
        assert body["name"] == "Fetch Test Worker"
        assert body["location"] == loc

    def test_get_nonexistent_worker_returns_404(self):
        r = client.get(f"/api/v1/workers/{uuid.uuid4()}")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 3. ML Risk calculation
# ---------------------------------------------------------------------------
class TestRisk:
    @pytest.fixture()
    def worker_id(self):
        r = client.post(
            "/api/v1/workers/register",
            json={"email": f"test_{uuid.uuid4().hex[:8]}@test.com", "password": "secure123", "name": "Risk Worker", "location": _loc(), "income": 1200},
        )
        return r.json()["worker_id"]

    def test_risk_calculate_returns_valid_score(self, worker_id):
        r = client.post(
            "/api/v1/risk/calculate",
            json={
                "worker_id": worker_id,
                "lat": 80.0, "lon": 70.0,
                "temperature": 32,
                "peak": True,
                "location_risk": 0.6,
                "hours": 3,
                "base_price": 20,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert 0.0 <= body["risk_score"] <= 1.0
        assert body["premium_quote"] > 0
        assert body["estimated_loss"] >= 0
        assert isinstance(body["fraud_flag"], bool)
        assert body["worker_id"] == worker_id

    def test_risk_unknown_worker_returns_404(self):
        r = client.post(
            "/api/v1/risk/calculate",
            json={
                "worker_id": str(uuid.uuid4()),
                "lat": 80.0, "lon": 70.0,
                "temperature": 28,
                "peak": False,
                "location_risk": 0.3,
                "hours": 2,
                "base_price": 20,
            },
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 4. Policy purchase
# ---------------------------------------------------------------------------
class TestPolicy:
    @pytest.fixture()
    def worker_with_risk(self):
        loc = _loc()
        reg = client.post(
            "/api/v1/workers/register",
            json={"email": f"test_{uuid.uuid4().hex[:8]}@test.com", "password": "secure123", "name": "Policy Worker", "location": loc, "income": 1000},
        )
        wid = reg.json()["worker_id"]
        client.post(
            "/api/v1/risk/calculate",
            json={
                "worker_id": wid,
                "lat": 80.0, "lon": 70.0,
                "temperature": 30,
                "peak": True,
                "location_risk": 0.5,
                "hours": 2,
                "base_price": 20,
            },
        )
        return wid

    def test_purchase_policy_success(self, worker_with_risk):
        r = client.post(
            "/api/v1/policy/purchase",
            json={"worker_id": worker_with_risk, "base_price": 20, "days": 7},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "active"
        assert body["worker_id"] == worker_with_risk
        assert body["premium"] > 0
        assert "policy_id" in body

    def test_policy_requires_existing_risk_profile(self):
        """Buying a policy without running ML first must fail."""
        reg = client.post(
            "/api/v1/workers/register",
            json={"email": f"test_{uuid.uuid4().hex[:8]}@test.com", "password": "secure123", "name": "No Risk Worker", "location": _loc(), "income": 500},
        )
        wid = reg.json()["worker_id"]
        r = client.post(
            "/api/v1/policy/purchase",
            json={"worker_id": wid, "base_price": 20, "days": 7},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 5. Event trigger
# ---------------------------------------------------------------------------
class TestEvent:
    @pytest.fixture()
    def insured_worker(self):
        """Register → run risk → buy policy, return (worker_id, location)."""
        loc = _loc()
        reg = client.post(
            "/api/v1/workers/register",
            json={"email": f"test_{uuid.uuid4().hex[:8]}@test.com", "password": "secure123", "name": "Event Worker", "location": loc, "income": 1000},
        )
        wid = reg.json()["worker_id"]
        client.post(
            "/api/v1/risk/calculate",
            json={
                "worker_id": wid,
                "lat": 90.0, "lon": 70.0,
                "temperature": 31,
                "peak": True,
                "location_risk": 0.6,
                "hours": 3,
                "base_price": 20,
            },
        )
        client.post(
            "/api/v1/policy/purchase",
            json={"worker_id": wid, "base_price": 20, "days": 7},
        )
        return wid, loc

    def test_rain_event_triggers_payout(self, insured_worker):
        _, loc = insured_worker
        r = client.post(
            "/api/v1/event/trigger",
            json={"location": loc, "lat": 90.0, "lon": 70.0},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["type"] == "rain"           # rainfall >= 50
        assert "event_id" in body
        assert body["payouts_processed"] >= 1

    def test_pollution_event_triggers_payout(self, insured_worker):
        _, loc = insured_worker
        r = client.post(
            "/api/v1/event/trigger",
            json={"location": loc, "lat": 10.0, "lon": 70.0},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["type"] == "pollution"      # aqi >= 300
        assert body["payouts_processed"] >= 1

    def test_no_event_when_thresholds_not_met(self, insured_worker):
        _, loc = insured_worker
        r = client.post(
            "/api/v1/event/trigger",
            json={"location": loc, "lat": 0.0, "lon": 70.0},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["type"] == "none"
        # No payout for a 'none' event
        assert body["payouts_processed"] == 0


# ---------------------------------------------------------------------------
# 6. Payout (idempotency)
# ---------------------------------------------------------------------------
class TestPayout:
    @pytest.fixture()
    def event_id_and_worker(self):
        """Full flow → returns (worker_id, event_id) with a payout NOT yet processed."""
        loc = _loc()
        reg = client.post(
            "/api/v1/workers/register",
            json={"email": f"test_{uuid.uuid4().hex[:8]}@test.com", "password": "secure123", "name": "Payout Worker", "location": loc, "income": 1000},
        )
        wid = reg.json()["worker_id"]
        client.post(
            "/api/v1/risk/calculate",
            json={
                "worker_id": wid,
                "lat": 80.0, "lon": 70.0,
                "temperature": 29,
                "peak": True,
                "location_risk": 0.5,
                "hours": 2,
                "base_price": 20,
            },
        )
        client.post(
            "/api/v1/policy/purchase",
            json={"worker_id": wid, "base_price": 20, "days": 7},
        )
        ev = client.post(
            "/api/v1/event/trigger",
            json={"location": loc, "lat": 80.0, "lon": 70.0},
        )
        eid = ev.json()["event_id"]
        return wid, eid

    def test_payout_process_success(self, event_id_and_worker):
        wid, eid = event_id_and_worker
        r = client.post(
            "/api/v1/payout/process",
            json={"worker_id": wid, "event_id": eid, "amount": 150.0},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] in {"processed", "already_processed"}
        assert body["amount"] >= 0
        assert "payout_id" in body

    def test_payout_is_idempotent(self, event_id_and_worker):
        """Sending the same (worker, event) twice must return the SAME payout_id."""
        wid, eid = event_id_and_worker
        first = client.post(
            "/api/v1/payout/process",
            json={"worker_id": wid, "event_id": eid, "amount": 200.0},
        )
        second = client.post(
            "/api/v1/payout/process",
            json={"worker_id": wid, "event_id": eid, "amount": 999.99},
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["payout_id"] == second.json()["payout_id"]
        assert second.json()["status"] == "already_processed"


# ---------------------------------------------------------------------------
# 7. Full end-to-end flow (one-shot simulation)
# ---------------------------------------------------------------------------
class TestEndToEnd:
    def test_full_simulation_flow(self):
        """
        Simulates the complete gig-worker lifecycle:
        register → risk → policy → event → payout
        All writes must persist in Supabase.
        """
        loc = _loc()

        # Step 1 — Register
        reg = client.post(
            "/api/v1/workers/register",
            json={"email": f"test_{uuid.uuid4().hex[:8]}@test.com", "password": "secure123", "name": "Full Flow Worker", "location": loc, "income": 1200},
        )
        assert reg.status_code == 200, reg.text
        wid = reg.json()["worker_id"]

        # Confirm worker is truly persisted
        fetch = client.get(f"/api/v1/workers/{wid}")
        assert fetch.status_code == 200
        assert fetch.json()["worker_id"] == wid

        # Step 2 — ML Risk
        risk = client.post(
            "/api/v1/risk/calculate",
            json={
                "worker_id": wid,
                "lat": 80.0, "lon": 70.0,
                "temperature": 33,
                "peak": True,
                "location_risk": 0.7,
                "hours": 4,
                "base_price": 20,
            },
        )
        assert risk.status_code == 200, risk.text
        risk_score = risk.json()["risk_score"]

        # Step 3 — Policy
        policy = client.post(
            "/api/v1/policy/purchase",
            json={"worker_id": wid, "base_price": 20, "days": 7},
        )
        assert policy.status_code == 200, policy.text
        assert policy.json()["status"] == "active"
        expected_premium = round(20 * (1 + risk_score), 2)
        assert abs(policy.json()["premium"] - expected_premium) < 0.01

        # Step 4 — Event (heavy rain)
        event = client.post(
            "/api/v1/event/trigger",
            json={"location": loc, "lat": 90.0, "lon": 70.0},
        )
        assert event.status_code == 200, event.text
        eid = event.json()["event_id"]
        assert event.json()["payouts_processed"] >= 1

        # Step 5 — Payout (idempotent)
        payout = client.post(
            "/api/v1/payout/process",
            json={"worker_id": wid, "event_id": eid, "amount": 120.0},
        )
        assert payout.status_code == 200, payout.text
        po_body = payout.json()
        assert po_body["status"] in {"processed", "already_processed"}
        assert po_body["worker_id"] == wid
        assert po_body["event_id"] == eid
