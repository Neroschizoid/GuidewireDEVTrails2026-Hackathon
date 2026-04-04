from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RegisterWorkerRequest(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)
    location: str = Field(min_length=1)
    income: float = Field(gt=0)


class LoginWorkerRequest(BaseModel):
    email: str
    password: str


class RegisterWorkerResponse(BaseModel):
    worker_id: str
    location: str
    active: bool
    shield: int = 0
    weekly_earnings: float = 0.0
    active_policy: bool = False
    access_token: str = ""
    refresh_token: str = ""


class WorkerInfoResponse(BaseModel):
    worker_id: str
    name: str
    email: str
    location: str
    income: float
    active: bool
    shield: int = 0
    weekly_earnings: float = 0.0
    active_policy: bool = False
    access_token: str = ""
    refresh_token: str = ""


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str


class RiskRequest(BaseModel):
    worker_id: str
    lat: float
    lon: float
    temperature: float = Field(ge=-30, le=70)
    peak: bool
    location_risk: float = Field(ge=0, le=1)
    hours: float = Field(ge=0, le=24)
    base_price: float = Field(ge=0, default=20)


class RiskResponse(BaseModel):
    worker_id: str
    risk_score: float
    premium_quote: float
    estimated_loss: float
    fraud_flag: bool
    recommended_tier: Optional[int] = None
    recommended_tier_name: Optional[str] = None
    temperature: float = 25.0
    peak_status: int = 0
    timestamp: datetime


class PurchasePolicyRequest(BaseModel):
    worker_id: str
    base_price: float = Field(ge=0)
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
    lat: float
    lon: float
    force_event_type: Optional[str] = None


class TriggerEventResponse(BaseModel):
    event_id: str
    type: str
    payouts_processed: int
    payouts_skipped: int


class PayoutResponse(BaseModel):
    payout_id: str
    status: str
    amount: float
    worker_id: str
    event_id: str


class PaymentRequest(BaseModel):
    worker_id: str
    p_id: int
    risk_score: float = 0.0
    premium: float = 0.0
    days: int = 7


class PaymentResponse(BaseModel):
    status: bool


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


# ─── Session ──────────────────────────────────────────────────
class SessionStartRequest(BaseModel):
    lat: float
    lon: float


class SessionStartResponse(BaseModel):
    session_id: str
    started_at: datetime


class SessionEndResponse(BaseModel):
    session_id: str
    ended_at: datetime


# ─── Check Triggers ───────────────────────────────────────────
class CheckTriggerRequest(BaseModel):
    session_id: str
    lat: float
    lon: float
    temperature: float = Field(ge=-30, le=70, default=30)
    peak: bool = True
    location_risk: float = Field(ge=0, le=1, default=0.5)
    hours: float = Field(ge=0, le=24, default=2)
    simulate: bool = False  # True injects rain=100, aqi=350 for demo


class CheckTriggerResponse(BaseModel):
    risk_score: float
    rain: float
    aqi: float
    triggered: bool
    trigger_type: Optional[str] = None   # "rain" | "aqi" | None
    payout: Optional[float] = None
    claim_id: Optional[str] = None
    message: str = ""
