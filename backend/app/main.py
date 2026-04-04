import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import event, payment, payout, policy, risk, session, trigger, worker
from app.core.db import Base, engine


app = FastAPI(title="Gig Worker Parametric Insurance API", version="1.0.0")

Base.metadata.create_all(bind=engine)

# Allow the React dev server to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔥 allow all for hackathon
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health() -> dict:
    return {"status": "ok"}

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.db import get_db


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
