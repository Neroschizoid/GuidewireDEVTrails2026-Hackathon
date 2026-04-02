from __future__ import annotations

from typing import Dict, List, Tuple

from app.models.entities import Event, FraudLog, Payout, Policy, RiskProfile, Worker


class InMemoryStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.workers: Dict[str, Worker] = {}
        self.risk_profiles: Dict[str, RiskProfile] = {}
        self.policies: Dict[str, Policy] = {}
        self.events: Dict[str, Event] = {}
        self.payouts: Dict[str, Payout] = {}
        self.payout_index: Dict[Tuple[str, str], str] = {}
        self.fraud_logs: List[FraudLog] = []


store = InMemoryStore()
