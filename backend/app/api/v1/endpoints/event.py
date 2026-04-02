from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.contracts import TriggerEventRequest, TriggerEventResponse
from app.services.event_service import trigger_event


router = APIRouter()


@router.post("/event/trigger", response_model=TriggerEventResponse)
def event_trigger(payload: TriggerEventRequest, db: Session = Depends(get_db)) -> TriggerEventResponse:
    return trigger_event(payload, db)
