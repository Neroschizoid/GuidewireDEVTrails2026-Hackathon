from fastapi.testclient import TestClient

from app.core.db import Base, engine
from app.main import app


client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_end_to_end_worker_risk_policy_event_payout() -> None:
    worker_res = client.post(
        "/api/v1/workers/register",
        json={"name": "Asha", "location": "blr-east", "income": 1000},
    )
    assert worker_res.status_code == 200
    worker_id = worker_res.json()["worker_id"]

    risk_res = client.post(
        "/api/v1/risk/calculate",
        json={
            "worker_id": worker_id,
            "rainfall": 120,
            "aqi": 320,
            "temperature": 31,
            "peak": True,
            "location_risk": 0.7,
            "hours": 3,
        },
    )
    assert risk_res.status_code == 200
    risk_body = risk_res.json()
    assert 0 <= risk_body["risk_score"] <= 1
    assert risk_body["premium_quote"] > 0
    assert risk_body["estimated_loss"] > 0

    policy_res = client.post(
        "/api/v1/policy/purchase",
        json={"worker_id": worker_id, "base_price": 20, "days": 7},
    )
    assert policy_res.status_code == 200
    assert policy_res.json()["status"] == "active"
    # Ensure policy pricing is synchronized with ML risk output.
    assert policy_res.json()["premium"] == round(20 * (1 + risk_body["risk_score"]), 2)

    event_res = client.post(
        "/api/v1/event/trigger",
        json={"location": "blr-east", "rainfall": 90, "aqi": 350},
    )
    assert event_res.status_code == 200
    event_body = event_res.json()
    assert event_body["type"] in {"rain", "pollution"}
    assert event_body["payouts_processed"] == 1


def test_payout_idempotency_same_worker_event() -> None:
    worker_res = client.post(
        "/api/v1/workers/register",
        json={"name": "Ravi", "location": "hyd-west", "income": 800},
    )
    worker_id = worker_res.json()["worker_id"]

    client.post(
        "/api/v1/risk/calculate",
        json={
            "worker_id": worker_id,
            "rainfall": 80,
            "aqi": 250,
            "temperature": 28,
            "peak": True,
            "location_risk": 0.5,
            "hours": 2,
        },
    )
    client.post(
        "/api/v1/policy/purchase",
        json={"worker_id": worker_id, "base_price": 20, "days": 7},
    )
    event_res = client.post(
        "/api/v1/event/trigger",
        json={"location": "hyd-west", "rainfall": 75, "aqi": 180},
    )
    event_id = event_res.json()["event_id"]

    first = client.post(
        "/api/v1/payout/process",
        json={"worker_id": worker_id, "event_id": event_id, "amount": 123.45},
    )
    second = client.post(
        "/api/v1/payout/process",
        json={"worker_id": worker_id, "event_id": event_id, "amount": 999.99},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["payout_id"] == second.json()["payout_id"]
    assert second.json()["status"] == "already_processed"
