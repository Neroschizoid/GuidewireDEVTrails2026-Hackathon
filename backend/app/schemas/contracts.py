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
    otp_code: Optional[str] = None


class RegisterWorkerResponse(BaseModel):
    worker_id: str
    location: str
    active: bool
    shield: int = 0
    weekly_earnings: float = 0.0
    active_policy: bool = False
    policy_start_date: Optional[datetime] = None
    policy_end_date: Optional[datetime] = None
    access_token: str = ""
    refresh_token: str = ""
    trust_score: float = 100.0
    two_factor_enabled: bool = False
    bank_account_linked: bool = False
    bank_account_masked: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_holder: Optional[str] = None
    preferred_payout_gateway: Optional[str] = None


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
    policy_start_date: Optional[datetime] = None
    policy_end_date: Optional[datetime] = None
    access_token: str = ""
    refresh_token: str = ""
    trust_score: float = 100.0
    two_factor_enabled: bool = False
    bank_account_linked: bool = False
    bank_account_masked: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_holder: Optional[str] = None
    preferred_payout_gateway: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


class RefreshTokenResponse(BaseModel):
    access_token: str


class TwoFactorSetupResponse(BaseModel):
    secret: str
    otp_auth_url: str
    manual_entry_key: str


class TwoFactorVerifyRequest(BaseModel):
    otp_code: str = Field(min_length=6, max_length=6)


class TwoFactorStatusResponse(BaseModel):
    enabled: bool
    message: str


class DeleteAccountResponse(BaseModel):
    deleted: bool
    worker_id: str
    message: str


class BankAccountRequest(BaseModel):
    account_holder: str = Field(min_length=2, max_length=120)
    bank_name: str = Field(min_length=2, max_length=120)
    account_number: str = Field(min_length=8, max_length=24)
    ifsc: str = Field(min_length=8, max_length=16)
    preferred_payout_gateway: Optional[str] = None


class BankAccountResponse(BaseModel):
    linked: bool
    verified: bool
    account_holder: Optional[str] = None
    bank_name: Optional[str] = None
    account_masked: Optional[str] = None
    ifsc: Optional[str] = None
    preferred_payout_gateway: Optional[str] = None
    message: str = ""


class GatewayOption(BaseModel):
    code: str
    name: str
    type: str
    description: str
    currency: Optional[str] = None
    public_key: Optional[str] = None
    is_configured: bool = False


class GatewayCatalogResponse(BaseModel):
    payment_gateways: list[GatewayOption]
    payout_gateways: list[GatewayOption]


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
    rain: float = 0.0
    aqi: float = 0.0
    location_risk: float = 0.0
    forecast_rainfall: float = 0.0
    forecast_aqi: float = 0.0
    temperature: float = 25.0
    peak_status: int = 0
    weather_unavailable: bool = False
    weather_error: Optional[str] = None
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
    fraud_score: float = 0.0
    fraud_reason: Optional[str] = None
    is_flagged: bool = False


class PaymentRequest(BaseModel):
    worker_id: str
    p_id: int
    risk_score: float = 0.0
    premium: float = 0.0
    days: int = 7
    payment_gateway: str = "razorpay_test"
    payment_reference: Optional[str] = None
    payment_status: str = "captured"
    payment_order_id: Optional[str] = None
    payment_signature: Optional[str] = None


class PaymentResponse(BaseModel):
    status: bool
    policy_id: Optional[str] = None
    premium: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    shield_id: int = 0
    payment_gateway: Optional[str] = None
    payment_reference: Optional[str] = None
    payment_status: str = "captured"
    message: str = ""


class CreatePaymentSessionRequest(BaseModel):
    worker_id: str
    p_id: int
    risk_score: float = 0.0
    premium: float = 0.0
    days: int = 7
    payment_gateway: str = "razorpay_test"


class PaymentSessionResponse(BaseModel):
    gateway: str
    key_id: Optional[str] = None
    order_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    description: str
    worker_name: str
    worker_email: str


class PayoutResult(BaseModel):
    payout_id: str
    worker_id: str
    event_id: str
    amount: float
    status: str
    fraud_score: float = 0.0
    fraud_reason: Optional[str] = None
    is_flagged: bool = False
    payout_gateway: Optional[str] = None
    payout_reference: Optional[str] = None
    transfer_status: str = "queued"
    beneficiary_masked: Optional[str] = None


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
    simulated_rainfall: Optional[float] = None
    simulated_aqi: Optional[float] = None


class CheckTriggerResponse(BaseModel):
    risk_score: float
    rain: float
    aqi: float
    location_risk: float = 0.0
    estimated_loss: float = 0.0
    forecast_rainfall: float = 0.0
    forecast_aqi: float = 0.0
    temperature: float = 25.0
    peak_status: int = 0
    weather_unavailable: bool = False
    weather_error: Optional[str] = None
    triggered: bool
    trigger_type: Optional[str] = None   # "rain" | "aqi" | None
    payout: Optional[float] = None
    claim_id: Optional[str] = None
    payout_gateway: Optional[str] = None
    payout_reference: Optional[str] = None
    transfer_status: Optional[str] = None
    beneficiary_masked: Optional[str] = None
    message: str = ""

class PayoutHistoryItem(BaseModel):
    payout_id: str
    event_id: str
    amount: float
    status: str
    is_flagged: bool
    trigger_type: str
    timestamp: datetime
    idempotency_key: str
    payout_gateway: Optional[str] = None
    payout_reference: Optional[str] = None
    transfer_status: str = "queued"
    beneficiary_masked: Optional[str] = None
