from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RegisterWorkerRequest(BaseModel):
    name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    income: float = Field(gt=0)


class RegisterWorkerResponse(BaseModel):
    worker_id: str
    location: str
    active: bool


class RiskRequest(BaseModel):
    worker_id: str
    rainfall: float = Field(ge=0, le=500)
    aqi: float = Field(ge=0, le=1000)
    temperature: float = Field(ge=-30, le=70)
    peak: bool
    location_risk: float = Field(ge=0, le=1)
    hours: float = Field(ge=0, le=24)


class RiskResponse(BaseModel):
    worker_id: str
    risk_score: float
    premium_quote: float
    estimated_loss: float
    fraud_flag: bool
    timestamp: datetime


class PurchasePolicyRequest(BaseModel):
    worker_id: str
    base_price: float = Field(gt=0)
    days: int = Field(gt=0, le=30)


class PurchasePolicyResponse(BaseModel):
    policy_id: str
    worker_id: str
    premium: float
    start_date: datetime
    end_date: datetime
    status: str


class TriggerEventRequest(BaseModel):
    location: str
    rainfall: float = Field(ge=0, le=500)
    aqi: float = Field(ge=0, le=1000)
    force_event_type: Optional[str] = None


class TriggerEventResponse(BaseModel):
    event_id: str
    type: str
    payouts_processed: int
    payouts_skipped: int


class PayoutResult(BaseModel):
    payout_id: str
    worker_id: str
    event_id: str
    amount: float
    status: str


class ProcessPayoutRequest(BaseModel):
    worker_id: str
    event_id: str
    amount: float = Field(ge=0)
