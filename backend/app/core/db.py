from __future__ import annotations

import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev_hackathon.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
elif "postgresql" in DATABASE_URL:
    connect_args["sslmode"] = "require"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _ensure_payout_created_at_column() -> None:
    inspector = inspect(engine)
    if "payouts" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("payouts")}
    if "created_at" in existing_columns:
        return

    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE payouts ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()"))
            conn.execute(text("UPDATE payouts SET created_at = NOW() WHERE created_at IS NULL"))
            conn.execute(text("ALTER TABLE payouts ALTER COLUMN created_at SET NOT NULL"))
        else:
            conn.execute(text("ALTER TABLE payouts ADD COLUMN created_at DATETIME"))
            conn.execute(text("UPDATE payouts SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))


def _ensure_worker_account_columns() -> None:
    inspector = inspect(engine)
    if "workers" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("workers")}
    column_defs = {
        "two_factor_enabled": "BOOLEAN DEFAULT 0" if engine.dialect.name != "postgresql" else "BOOLEAN DEFAULT FALSE",
        "two_factor_secret": "VARCHAR",
        "bank_account_holder": "VARCHAR",
        "bank_name": "VARCHAR",
        "bank_account_number": "VARCHAR",
        "bank_ifsc": "VARCHAR",
        "bank_account_verified": "BOOLEAN DEFAULT 0" if engine.dialect.name != "postgresql" else "BOOLEAN DEFAULT FALSE",
        "preferred_payout_gateway": "VARCHAR",
    }

    with engine.begin() as conn:
        for column_name, column_type in column_defs.items():
            if column_name in existing_columns:
                continue
            if engine.dialect.name == "postgresql":
                conn.execute(text(f"ALTER TABLE workers ADD COLUMN IF NOT EXISTS {column_name} {column_type}"))
            else:
                conn.execute(text(f"ALTER TABLE workers ADD COLUMN {column_name} {column_type}"))


def _ensure_policy_payment_columns() -> None:
    inspector = inspect(engine)
    if "policies" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("policies")}
    column_defs = {
        "payment_gateway": "VARCHAR",
        "payment_reference": "VARCHAR",
        "payment_status": "VARCHAR DEFAULT 'captured'" if engine.dialect.name == "postgresql" else "VARCHAR DEFAULT 'captured'",
    }
    with engine.begin() as conn:
        for column_name, column_type in column_defs.items():
            if column_name in existing_columns:
                continue
            if engine.dialect.name == "postgresql":
                conn.execute(text(f"ALTER TABLE policies ADD COLUMN IF NOT EXISTS {column_name} {column_type}"))
            else:
                conn.execute(text(f"ALTER TABLE policies ADD COLUMN {column_name} {column_type}"))


def _ensure_payout_gateway_columns() -> None:
    inspector = inspect(engine)
    if "payouts" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("payouts")}
    column_defs = {
        "payout_gateway": "VARCHAR",
        "payout_reference": "VARCHAR",
        "transfer_status": "VARCHAR DEFAULT 'queued'" if engine.dialect.name == "postgresql" else "VARCHAR DEFAULT 'queued'",
        "beneficiary_masked": "VARCHAR",
    }
    with engine.begin() as conn:
        for column_name, column_type in column_defs.items():
            if column_name in existing_columns:
                continue
            if engine.dialect.name == "postgresql":
                conn.execute(text(f"ALTER TABLE payouts ADD COLUMN IF NOT EXISTS {column_name} {column_type}"))
            else:
                conn.execute(text(f"ALTER TABLE payouts ADD COLUMN {column_name} {column_type}"))


def _seed_shields() -> None:
    shields = {
        0: "No Shield",
        1: "Basic Shield",
        2: "Pro Armor",
        3: "Elite Armor",
    }
    with SessionLocal() as db:
        for p_id, name in shields.items():
            db.execute(
                text(
                    """
                    INSERT INTO shields (p_id, name)
                    VALUES (:p_id, :name)
                    ON CONFLICT (p_id) DO UPDATE SET name = EXCLUDED.name
                    """
                ),
                {"p_id": p_id, "name": name},
            )
        db.commit()


def bootstrap_database() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_payout_created_at_column()
    _ensure_worker_account_columns()
    _ensure_policy_payment_columns()
    _ensure_payout_gateway_columns()
    _seed_shields()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
