import os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.db_models import WorkerDB

SECRET_KEY = os.getenv("SECRET_KEY", "parametric_dev_super_secret_key_123!")
ALGORITHM = "HS256"

# Hardcoded for business parameters. Access: 15 mins. Refresh: 7 days.
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/workers/login")

def create_access_token(worker_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": worker_id, "exp": expire, "type": "access"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(worker_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": worker_id, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_worker(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> WorkerDB:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        worker_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if worker_id is None or token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token signature")
        
    worker = db.get(WorkerDB, worker_id)
    if worker is None:
        raise HTTPException(status_code=401, detail="Worker user not found")
        
    return worker
