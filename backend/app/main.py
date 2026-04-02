from fastapi import FastAPI

from app.api.v1.endpoints import event, payout, policy, risk, worker
from app.core.db import Base, engine


app = FastAPI(title="Gig Worker Parametric Insurance API", version="1.0.0")

Base.metadata.create_all(bind=engine)


@app.get("/")
def health() -> dict:
    return {"status": "ok"}


app.include_router(worker.router, prefix="/api/v1", tags=["worker"])
app.include_router(risk.router, prefix="/api/v1", tags=["risk"])
app.include_router(policy.router, prefix="/api/v1", tags=["policy"])
app.include_router(event.router, prefix="/api/v1", tags=["event"])
app.include_router(payout.router, prefix="/api/v1", tags=["payout"])
