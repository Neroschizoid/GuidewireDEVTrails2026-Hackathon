import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.endpoints import event, payment, payout, policy, risk, session, trigger, worker
from app.core.db import bootstrap_database, get_db
from app.core.security import ensure_security_configuration


def _get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


ensure_security_configuration()

app = FastAPI(title="Gig Worker Parametric Insurance API", version="1.0.0")

bootstrap_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/")
def health() -> dict:
    return {"status": "ok"}


@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1")).fetchone()
    return {"result": result[0]}


app.include_router(worker.router, prefix="/api/v1", tags=["worker"])
app.include_router(risk.router, prefix="/api/v1", tags=["risk"])
app.include_router(policy.router, prefix="/api/v1", tags=["policy"])
app.include_router(event.router, prefix="/api/v1", tags=["event"])
app.include_router(payout.router, prefix="/api/v1", tags=["payout"])
app.include_router(payment.router, prefix="/api/v1", tags=["payment"])
app.include_router(session.router, prefix="/api/v1", tags=["session"])
app.include_router(trigger.router, prefix="/api/v1", tags=["trigger"])

from app.api.v1.endpoints import admin

app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
