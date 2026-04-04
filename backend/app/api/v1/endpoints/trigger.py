from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_worker
from app.ml.inference import run_inference
from app.models.db_models import (
    EventDB, PayoutDB, PolicyDB, TriggerStateDB, WorkerDB, WorkerSessionDB,
)
from app.schemas.contracts import CheckTriggerRequest, CheckTriggerResponse
from app.services.payout_service import process_payout
from app.services.validation_service import validate_eligibility_for_payout
from app.services.weather_service import fetch_live_weather

router = APIRouter()

RAIN_THRESHOLD = 50.0   # mm — rainfall triggers a claim
AQI_THRESHOLD = 200.0   # AQI units — hazardous band


def _compute_payout(rainfall: float, aqi: float) -> float:
    return round(max((rainfall * 1.2) + (aqi * 0.2), 0.0), 2)


def _get_or_create_trigger_state(
    session_id: str, trigger_type: str, db: Session
) -> TriggerStateDB:
    state = db.scalar(
        select(TriggerStateDB).where(
            TriggerStateDB.session_id == session_id,
            TriggerStateDB.trigger_type == trigger_type,
        )
    )
    if state is None:
        # Lazy creation in case session.start didn't seed it (defensive)
        state = TriggerStateDB(
            id=str(uuid.uuid4()),
            session_id=session_id,
            trigger_type=trigger_type,
            active=False,
            last_triggered_at=None,
        )
        db.add(state)
        db.flush()
    return state


@router.post("/triggers/check", response_model=CheckTriggerResponse)
def check_triggers(
    payload: CheckTriggerRequest,
    db: Session = Depends(get_db),
    current_worker: WorkerDB = Depends(get_current_worker),
) -> CheckTriggerResponse:
    """
    Core automation engine. Called by the frontend every 2.5 minutes while ONLINE.

    1. Validate session belongs to current worker and is active.
    2. Fetch live weather (or inject simulated values).
    3. Run ML risk model.
    4. Evaluate trigger conditions (rain > 50, AQI > 200).
    5. Apply idempotent state machine per (session_id, trigger_type).
    6. Auto-create a claim (EventDB + PayoutDB) when a new trigger fires.
    7. Reset trigger state when condition clears.
    """
    # ── 1. Validate session ──────────────────────────────────────
    session = db.get(WorkerSessionDB, payload.session_id)
    if session is None or session.worker_id != current_worker.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    # ── 2. Fetch weather (or simulate) ──────────────────────────
    if payload.simulate:
        rainfall, aqi, temp = 100.0, 350.0, 32.0
    else:
        rainfall, aqi, temp = fetch_live_weather(payload.lat, payload.lon)

    # ── 3. ML risk model ─────────────────────────────────────────
    from app.services.weather_service import get_peak_hour
    peak = get_peak_hour()
    loc_risk = 0.6  # static as requested

    inference = run_inference(
        rainfall=rainfall,
        aqi=aqi,
        temperature=temp,
        peak=bool(peak),
        location_risk=loc_risk,
        income=current_worker.income,
        hours=payload.hours,
        active=current_worker.active,
        paid=False,
        base_price=20.0,
    )

    # ── 4. Evaluate triggers ─────────────────────────────────────
    conditions = {
        "rain": rainfall > RAIN_THRESHOLD,
        "aqi": aqi > AQI_THRESHOLD,
    }

    triggered = False
    trigger_type_fired: str | None = None
    payout_amount: float | None = None
    claim_id: str | None = None
    message = "Monitoring active — no trigger conditions met."

    for t_type, condition_met in conditions.items():
        state = _get_or_create_trigger_state(payload.session_id, t_type, db)

        if condition_met and not state.active:
            # ── New trigger: fire a claim ──────────────────────────
            # Verify worker has an active policy (7-day window)
            policy = db.scalar(
                select(PolicyDB).where(PolicyDB.worker_id == current_worker.id)
            )
            now = datetime.now(timezone.utc)
            has_policy = False
            if policy and policy.status == "active":
                p_start = policy.start_date if policy.start_date.tzinfo else policy.start_date.replace(tzinfo=timezone.utc)
                p_end = policy.end_date if policy.end_date.tzinfo else policy.end_date.replace(tzinfo=timezone.utc)
                has_policy = p_start <= now <= p_end

            if has_policy:
                severity = "high" if rainfall >= 80 or aqi >= 400 else "medium"
                event = EventDB(
                    id=str(uuid.uuid4()),
                    type=t_type,
                    severity=severity,
                    location=current_worker.location,
                    rainfall=rainfall,
                    aqi=aqi,
                    timestamp=now,
                )
                db.add(event)
                db.flush()

                amount = _compute_payout(rainfall, aqi)
                payout_result = process_payout(
                    worker=current_worker,
                    event=event,
                    amount=amount,
                    db=db,
                )

                # Update trigger state to active (lock until condition clears)
                state.active = True
                state.last_triggered_at = now

                triggered = True
                trigger_type_fired = t_type
                payout_amount = payout_result.amount
                claim_id = payout_result.payout_id
                message = (
                    f"{'Simulated ' if payload.simulate else ''}"
                    f"{t_type.upper()} trigger fired — "
                    f"₹{payout_result.amount:.0f} claim created."
                )
                # Break after first trigger to keep one claim per check cycle
                break

        elif condition_met and state.active:
            # Condition still true — already fired this cycle, do nothing
            message = f"{t_type.upper()} condition still active — payout already issued for this cycle."

        elif not condition_met and state.active:
            # Condition cleared — reset so next event cycle can fire again
            state.active = False
            message = f"{t_type.upper()} condition cleared — ready for next event cycle."

    db.commit()

    return CheckTriggerResponse(
        risk_score=round(inference.risk_score, 4),
        rain=rainfall,
        aqi=aqi,
        temperature=temp,
        peak_status=peak,
        triggered=triggered,
        trigger_type=trigger_type_fired,
        payout=payout_amount,
        claim_id=claim_id,
        message=message,
    )
