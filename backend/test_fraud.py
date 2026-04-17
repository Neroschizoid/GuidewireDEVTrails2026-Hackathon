import math
from datetime import datetime, timezone, timedelta
from app.models.db_models import WorkerDB, WorkerSessionDB
from app.services.fraud_service import calculate_fraud_score

def test_gps_velocity():
    # Helper to test haversine logic locally without db initially
    worker = WorkerDB(id="w1", trust_score=100.0)
    now = datetime.now(timezone.utc)
    
    session = WorkerSessionDB(
        id="s1", 
        worker_id="w1", 
        last_lat=12.9716, 
        last_lon=77.5946, 
        last_ping_at=now - timedelta(minutes=5)
    )
    
    # 5 minutes later, the worker is suddenly 100km away (extremely fast, ~1200 km/h)
    new_lat = 13.8  # ~100 km north roughly
    new_lon = 77.6
    
    class FakeQuery:
        def filter(self, *args): return self
        def join(self, *args): return self
        def order_by(self, *args): return self
        def first(self): return None
        
    class FakeDB:
        def query(self, *args): return FakeQuery()
        def commit(self): pass

    score, reason = calculate_fraud_score(worker, session, "rain", new_lat, new_lon, FakeDB())
    print(f"Test 1 - Very Fast Velocity -> Score: {score}, Reason: {reason}")
    assert score >= 85

    # Test 2 - Normal Velocity
    session2 = WorkerSessionDB(
        id="s2", 
        worker_id="w1", 
        last_lat=12.9716, 
        last_lon=77.5946, 
        last_ping_at=now - timedelta(hours=1)
    )
    
    score2, reason2 = calculate_fraud_score(worker, session2, "rain", 12.98, 77.60, FakeDB())
    print(f"Test 2 - Normal Velocity -> Score: {score2}, Reason: {reason2}")
    assert score2 == 0.0

if __name__ == "__main__":
    test_gps_velocity()
    print("All basic fraud logic tests passed!")

