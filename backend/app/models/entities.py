from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Worker:
    id: str
    name: str
    email: str
    hashed_password: str
    location: str
    income: float
    active: bool = True


@dataclass
class RiskProfile:
    worker_id: str
    risk_score: float
    timestamp: datetime


@dataclass
class Policy:
    id: str
    worker_id: str
    risk_score: float
    premium: float
    start_date: datetime
    end_date: datetime
    status: str = "active"


@dataclass
class Event:
    id: str
    type: str
    severity: str
    location: str
    rainfall: float
    aqi: float
    timestamp: datetime


@dataclass
class Payout:
    id: str
    worker_id: str
    event_id: str
    amount: float
    status: str
    idempotency_key: str


@dataclass
class FraudLog:
    worker_id: str
    event_id: Optional[str]
    reason: str
    timestamp: datetime
