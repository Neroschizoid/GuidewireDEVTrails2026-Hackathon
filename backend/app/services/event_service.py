from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import EventDB, WorkerDB
from app.schemas.contracts import TriggerEventRequest, TriggerEventResponse
from app.services.payout_service import process_payout
from app.services.validation_service import validate_for_payout
from app.services.weather_service import fetch_live_weather


def _infer_event_type(rainfall: float, aqi: float, force_event_type: str | None) -> str:
    if force_event_type:
        return force_event_type
    if rainfall >= 50:
        return "rain"
    if aqi >= 300:
        return "pollution"
    return "none"


def trigger_event(payload: TriggerEventRequest, db: Session) -> TriggerEventResponse:
    rainfall, aqi = fetch_live_weather(payload.lat, payload.lon)
    event_type = _infer_event_type(rainfall, aqi, payload.force_event_type)
    severity = "high" if rainfall >= 80 or aqi >= 400 else "medium"

    event = EventDB(
        id=str(uuid.uuid4()),
        type=event_type,
        severity=severity,
        location=payload.location,
        rainfall=rainfall,
        aqi=aqi,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    processed = 0
    skipped = 0
    workers = db.scalars(select(WorkerDB).where(WorkerDB.location == payload.location)).all()
    for worker in workers:
        if not validate_for_payout(worker, event, db):
            skipped += 1
            continue

        # Deterministic payout rule for event-based compensation.
        amount = max((rainfall * 1.2) + (aqi * 0.2), 0.0)
        result = process_payout(worker=worker, event=event, amount=amount, db=db)
        if result.status == "processed":
            processed += 1
        else:
            skipped += 1

    return TriggerEventResponse(
        event_id=event.id,
        type=event.type,
        payouts_processed=processed,
        payouts_skipped=skipped,
    )
