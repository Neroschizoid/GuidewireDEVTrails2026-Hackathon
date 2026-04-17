import math
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import WorkerDB, WorkerSessionDB, PayoutDB, EventDB

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_fraud_score(worker: WorkerDB, session: WorkerSessionDB, event_type: str, current_lat: float, current_lon: float, db: Session) -> Tuple[float, Optional[str]]:
    """
    Calculate fraud score based on velocity, duplicate payouts, and worker trust.
    Returns: (fraud_score, fraud_reason)
    """
    score = 0.0
    reasons = []
    now = datetime.now(timezone.utc)

    # 1. GPS Spoofing Detection
    if session.last_lat is not None and session.last_lon is not None and session.last_ping_at is not None:
        last_ping = session.last_ping_at
        if last_ping.tzinfo is None:
            last_ping = last_ping.replace(tzinfo=timezone.utc)
            
        time_diff_hours = (now - last_ping).total_seconds() / 3600.0
        
        # Only check if the time difference is extremely small or normal, if it's been days, it's a new session basically
        if 0 < time_diff_hours < 24:
            distance_km = haversine(session.last_lat, session.last_lon, current_lat, current_lon)
            velocity = distance_km / time_diff_hours
            
            if velocity > 120.0:  # Unrealistic speed
                score += 85.0
                reasons.append(f"Impossible traversal velocity ({velocity:.1f} km/h)")
            elif velocity > 80.0:
                score += 40.0
                reasons.append(f"High traversal velocity ({velocity:.1f} km/h)")

    # 2. Duplicate Detection (check recent claims for the same worker)
    # Get the latest payout for this worker to see if there's excessive claiming
    recent_payouts = db.query(PayoutDB).join(EventDB).filter(
        PayoutDB.worker_id == worker.id
    ).order_by(EventDB.timestamp.desc()).first()

    if recent_payouts:
        last_event = db.query(EventDB).filter(EventDB.id == recent_payouts.event_id).first()
        if last_event:
            last_timestamp = last_event.timestamp
            if last_timestamp.tzinfo is None:
                last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
            
            hours_since_last_claim = (now - last_timestamp).total_seconds() / 3600.0
            if hours_since_last_claim < 2.0:
                score += 80.0
                reasons.append(f"Frequent claims (< 2h window)")

    # 3. Worker Trust Penalty
    if worker.trust_score < 50.0:
        score += 20.0
        reasons.append(f"Low worker trust score ({worker.trust_score})")

    # Update session last ping
    session.last_lat = current_lat
    session.last_lon = current_lon
    session.last_ping_at = now
    
    # Bound score
    score = min(max(score, 0.0), 100.0)
    
    fraud_reason = " | ".join(reasons) if reasons else None

    # Apply penalty to trust score if serious fraud
    if score >= 70:
        worker.trust_score = max(0.0, worker.trust_score - 10.0)

    db.commit()

    return score, fraud_reason
