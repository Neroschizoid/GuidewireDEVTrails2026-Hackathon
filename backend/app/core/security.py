import os
import base64
import hashlib
import hmac
import secrets
import struct
import urllib.parse
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.db_models import WorkerDB

ALGORITHM = "HS256"

# Hardcoded for business parameters. Access: 15 mins. Refresh: 7 days.
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
REFRESH_COOKIE_NAME = "gw_refresh_token"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/workers/login")


def get_secret_key() -> str:
    secret_key = os.getenv("JWT_SECRET")
    if not secret_key:
        raise RuntimeError("JWT_SECRET environment variable must be set")
    return secret_key


def ensure_security_configuration() -> None:
    get_secret_key()


def _env_flag(var_name: str, default: bool) -> bool:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _refresh_cookie_secure() -> bool:
    return _env_flag("COOKIE_SECURE", False)


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=_refresh_cookie_secure(),
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/workers",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=_refresh_cookie_secure(),
        samesite="lax",
        path="/api/v1/workers",
    )


def _parse_csv_env(var_name: str) -> set[str]:
    raw = os.getenv(var_name, "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def is_admin_worker(worker: WorkerDB) -> bool:
    admin_ids = _parse_csv_env("ADMIN_WORKER_IDS")
    admin_emails = {email.lower() for email in _parse_csv_env("ADMIN_EMAILS")}
    return worker.id in admin_ids or worker.email.lower() in admin_emails


def create_access_token(worker_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": worker_id, "exp": expire, "type": "access"}
    return jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)

def create_refresh_token(worker_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": worker_id, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")


def build_totp_uri(secret: str, account_name: str, issuer: str = "Parametric Shield") -> str:
    label = urllib.parse.quote(f"{issuer}:{account_name}")
    issuer_q = urllib.parse.quote(issuer)
    secret_q = urllib.parse.quote(secret)
    return f"otpauth://totp/{label}?secret={secret_q}&issuer={issuer_q}&algorithm=SHA1&digits=6&period=30"


def generate_totp_code(secret: str, timestamp: int | None = None, period: int = 30) -> str:
    if timestamp is None:
        timestamp = int(datetime.now(timezone.utc).timestamp())

    normalized_secret = secret.upper()
    padding = "=" * ((8 - len(normalized_secret) % 8) % 8)
    key = base64.b32decode(normalized_secret + padding, casefold=True)
    counter = int(timestamp // period)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % 1_000_000).zfill(6)


def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    if not code or not code.isdigit():
        return False

    now = int(datetime.now(timezone.utc).timestamp())
    for offset in range(-window, window + 1):
        candidate = generate_totp_code(secret, timestamp=now + (offset * 30))
        if hmac.compare_digest(candidate, code):
            return True
    return False

def get_current_worker(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> WorkerDB:
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
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


def get_current_admin_worker(
    current_worker: WorkerDB = Depends(get_current_worker),
) -> WorkerDB:
    if not is_admin_worker(current_worker):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_worker
