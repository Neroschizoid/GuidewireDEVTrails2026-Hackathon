from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_admin_worker
from app.models.db_models import WorkerDB
from app.schemas.contracts import TriggerEventRequest, TriggerEventResponse
from app.services.event_service import trigger_event


router = APIRouter()


@router.post("/event/trigger", response_model=TriggerEventResponse)
def event_trigger(
    payload: TriggerEventRequest,
    db: Session = Depends(get_db),
    current_admin: WorkerDB = Depends(get_current_admin_worker),
) -> TriggerEventResponse:
    return trigger_event(payload, db)
