from __future__ import annotations

import os
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
from app.services.analytics_service import estimate_location_risk
from app.services.weather_service import fetch_weather_snapshot

router = APIRouter()

RAIN_THRESHOLD = 50.0   # mm — rainfall triggers a claim
AQI_THRESHOLD = 200.0   # AQI units — hazardous band


def _tier_limit(shield_id: int) -> float:
    limits = {
        0: 0.0,
        1: 150.0,
        2: 300.0,
        3: 450.0,
    }
    return limits.get(shield_id, 150.0)


def _compute_payout(
    rainfall: float,
    aqi: float,
    estimated_loss: float,
    shield_id: int,
    forecast_rainfall: float,
    forecast_aqi: float,
) -> float:
    weather_component = max((rainfall * 1.15) + (aqi * 0.18), 0.0)
    forecast_component = max((forecast_rainfall * 0.45) + (forecast_aqi * 0.06), 0.0)
    modeled = max(estimated_loss * 1.1, weather_component + forecast_component)
    return round(min(_tier_limit(shield_id), modeled), 2)


def _condition_source(current_value: float, forecast_value: float, threshold: float) -> str:
    if current_value >= threshold:
        return "current"
    if forecast_value >= threshold:
        return "forecast"
    return "none"


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
    allow_simulation = os.getenv("ALLOW_TRIGGER_SIMULATION", "false").lower() == "true"
    if payload.simulate and not allow_simulation:
        raise HTTPException(status_code=400, detail="Trigger simulation is disabled in this environment")

    if payload.simulate:
        rainfall = payload.simulated_rainfall if payload.simulated_rainfall is not None else 100.0
        aqi = payload.simulated_aqi if payload.simulated_aqi is not None else max(220.0, rainfall * 1.8)
        temp = 32.0
        forecast_rainfall = rainfall * 1.2
        forecast_aqi = aqi * 1.05
    else:
        snapshot = fetch_weather_snapshot(payload.lat, payload.lon)
        rainfall = snapshot.current_rainfall
        aqi = snapshot.current_aqi
        temp = snapshot.current_temperature
        forecast_rainfall = max(snapshot.next_24h_rainfall, rainfall)
        forecast_aqi = max(snapshot.next_24h_peak_aqi, aqi)

    effective_rainfall = max(rainfall, forecast_rainfall)
    effective_aqi = max(aqi, forecast_aqi)
    rain_source = _condition_source(rainfall, forecast_rainfall, RAIN_THRESHOLD)
    aqi_source = _condition_source(aqi, forecast_aqi, AQI_THRESHOLD)

    # ── 3. ML risk model ─────────────────────────────────────────
    from app.services.weather_service import get_peak_hour
    peak = get_peak_hour()
    loc_risk = estimate_location_risk(
        db=db,
        location=current_worker.location,
        current_rainfall=rainfall,
        current_aqi=aqi,
        forecast_rainfall=forecast_rainfall,
        forecast_aqi=forecast_aqi,
    )

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
        "rain": effective_rainfall >= RAIN_THRESHOLD,
        "aqi": effective_aqi >= AQI_THRESHOLD,
    }

    triggered = False
    trigger_type_fired: str | None = None
    payout_amount: float | None = None
    claim_id: str | None = None
    payout_gateway: str | None = None
    payout_reference: str | None = None
    transfer_status: str | None = None
    beneficiary_masked: str | None = None
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
                severity = "high" if effective_rainfall >= 80 or effective_aqi >= 400 else "medium"
                event = EventDB(
                    id=str(uuid.uuid4()),
                    type=t_type,
                    severity=severity,
                    location=current_worker.location,
                    rainfall=effective_rainfall,
                    aqi=effective_aqi,
                    timestamp=now,
                )
                db.add(event)
                db.flush()

                from app.services.fraud_service import calculate_fraud_score
                fraud_score, fraud_reason = calculate_fraud_score(
                    worker=current_worker,
                    session=session,
                    event_type=t_type,
                    current_lat=payload.lat,
                    current_lon=payload.lon,
                    db=db
                )

                amount = _compute_payout(
                    rainfall=rainfall,
                    aqi=aqi,
                    estimated_loss=inference.estimated_loss,
                    shield_id=current_worker.shield,
                    forecast_rainfall=forecast_rainfall,
                    forecast_aqi=forecast_aqi,
                )
                payout_result = process_payout(
                    worker=current_worker,
                    event=event,
                    amount=amount,
                    db=db,
                    fraud_score=fraud_score,
                    fraud_reason=fraud_reason,
                    is_flagged=(fraud_score >= 70.0)
                )

                # Update trigger state to active (lock until condition clears)
                state.active = True
                state.last_triggered_at = now

                triggered = True
                trigger_type_fired = t_type
                payout_amount = payout_result.amount
                claim_id = payout_result.payout_id
                payout_gateway = payout_result.payout_gateway
                payout_reference = payout_result.payout_reference
                transfer_status = payout_result.transfer_status
                beneficiary_masked = payout_result.beneficiary_masked
                trigger_source = rain_source if t_type == "rain" else aqi_source
                message = (
                    f"{'Simulated ' if payload.simulate else ''}"
                    f"{t_type.upper()} trigger fired from {trigger_source} conditions — "
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
        location_risk=round(loc_risk, 4),
        estimated_loss=round(inference.estimated_loss, 2),
        forecast_rainfall=round(forecast_rainfall, 2),
        forecast_aqi=round(forecast_aqi, 2),
        temperature=temp,
        peak_status=peak,
        weather_unavailable=(False if payload.simulate else not snapshot.available),
        weather_error=(None if payload.simulate else snapshot.error),
        triggered=triggered,
        trigger_type=trigger_type_fired,
        payout=payout_amount,
        claim_id=claim_id,
        payout_gateway=payout_gateway,
        payout_reference=payout_reference,
        transfer_status=transfer_status,
        beneficiary_masked=beneficiary_masked,
        message=message,
    )
