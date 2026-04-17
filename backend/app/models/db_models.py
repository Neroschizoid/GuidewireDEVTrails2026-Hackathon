from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _uuid() -> str:
    return str(uuid4())


class ShieldTierDB(Base):
    __tablename__ = "shields"
    p_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class WorkerDB(Base):
    __tablename__ = "workers"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False, index=True)
    income: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    shield: Mapped[int] = mapped_column(ForeignKey("shields.p_id"), default=0, nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    two_factor_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    bank_account_holder: Mapped[str | None] = mapped_column(String, nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String, nullable=True)
    bank_account_number: Mapped[str | None] = mapped_column(String, nullable=True)
    bank_ifsc: Mapped[str | None] = mapped_column(String, nullable=True)
    bank_account_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    preferred_payout_gateway: Mapped[str | None] = mapped_column(String, nullable=True)


class RiskProfileDB(Base):
    __tablename__ = "risk_profiles"
    worker_id: Mapped[str] = mapped_column(String, ForeignKey("workers.id"), primary_key=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PolicyDB(Base):
    __tablename__ = "policies"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    worker_id: Mapped[str] = mapped_column(String, ForeignKey("workers.id"), unique=True, index=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    premium: Mapped[float] = mapped_column(Float, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    payment_gateway: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_status: Mapped[str] = mapped_column(String, default="captured", nullable=False)


class EventDB(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rainfall: Mapped[float] = mapped_column(Float, nullable=False)
    aqi: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PayoutDB(Base):
    __tablename__ = "payouts"
    __table_args__ = (UniqueConstraint("worker_id", "event_id", name="uq_worker_event"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    worker_id: Mapped[str] = mapped_column(String, ForeignKey("workers.id"), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String, ForeignKey("events.id"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="processed")
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    fraud_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fraud_reason: Mapped[str] = mapped_column(String, nullable=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payout_gateway: Mapped[str | None] = mapped_column(String, nullable=True)
    payout_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    transfer_status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
    beneficiary_masked: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class WorkerSessionDB(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    worker_id: Mapped[str] = mapped_column(String, ForeignKey("workers.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)  # active | ended
    last_lat: Mapped[float] = mapped_column(Float, nullable=True)
    last_lon: Mapped[float] = mapped_column(Float, nullable=True)
    last_ping_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class TriggerStateDB(Base):
    __tablename__ = "trigger_state"
    __table_args__ = (UniqueConstraint("session_id", "trigger_type", name="uq_session_trigger"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String, nullable=False)  # rain | aqi
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
