from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.db_models import EventDB, PayoutDB, PolicyDB, WorkerDB
from app.services.weather_service import ForecastPoint, fetch_weather_snapshot, geocode_location


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class LocationContext:
    location: str
    lat: float
    lon: float
    active_workers: int


@dataclass
class AdminStatsSnapshot:
    total_workers_protected: int
    active_weekly_coverage: int
    protected_earnings_estimate: float
    claims_premium_ratio: float
    loss_ratio_percent: float
    fraud_savings: float
    avg_payout_time: str
    predicted_next_week_claims: int
    predicted_next_week_loss: float
    highest_risk_day: Optional[str]
    forecast_location: Optional[str]
    weather_unavailable: bool


def get_primary_location_context(
    db: Session,
    location: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> LocationContext:
    resolved_location = location

    if resolved_location is None:
        resolved_location = db.execute(
            select(WorkerDB.location)
            .join(PolicyDB, PolicyDB.worker_id == WorkerDB.id)
            .where(PolicyDB.status == "active")
            .group_by(WorkerDB.location)
            .order_by(func.count().desc(), WorkerDB.location.asc())
            .limit(1)
        ).scalar_one_or_none()

    if resolved_location is None:
        resolved_location = db.execute(
            select(WorkerDB.location)
            .group_by(WorkerDB.location)
            .order_by(func.count().desc(), WorkerDB.location.asc())
            .limit(1)
        ).scalar_one_or_none() or "Bengaluru"

    if lat is None or lon is None:
        lat, lon = geocode_location(resolved_location)

    active_workers = db.scalar(
        select(func.count())
        .select_from(WorkerDB)
        .join(PolicyDB, PolicyDB.worker_id == WorkerDB.id, isouter=True)
        .where(
            WorkerDB.location == resolved_location,
            WorkerDB.active.is_(True),
            PolicyDB.status == "active",
        )
    ) or 0

    return LocationContext(
        location=resolved_location,
        lat=float(lat),
        lon=float(lon),
        active_workers=int(active_workers),
    )


def estimate_location_risk(
    db: Session,
    location: str,
    current_rainfall: float,
    current_aqi: float,
    forecast_rainfall: float,
    forecast_aqi: float,
) -> float:
    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=30)

    event_counts = db.execute(
        select(
            func.count(EventDB.id),
            func.sum(case((EventDB.severity == "high", 1), else_=0)),
            func.avg(EventDB.rainfall),
            func.avg(EventDB.aqi),
        ).where(
            EventDB.location == location,
            EventDB.timestamp >= lookback,
        )
    ).one()

    payout_metrics = db.execute(
        select(
            func.count(PayoutDB.id),
            func.avg(PayoutDB.amount),
        )
        .join(EventDB, EventDB.id == PayoutDB.event_id)
        .where(
            EventDB.location == location,
            EventDB.timestamp >= lookback,
            PayoutDB.is_flagged.is_(False),
        )
    ).one()

    active_workers = db.scalar(
        select(func.count())
        .select_from(WorkerDB)
        .where(WorkerDB.location == location, WorkerDB.active.is_(True))
    ) or 0

    event_count = int(event_counts[0] or 0)
    high_severity_count = int(event_counts[1] or 0)
    avg_rainfall = float(event_counts[2] or 0.0)
    avg_aqi = float(event_counts[3] or 0.0)
    payout_count = int(payout_metrics[0] or 0)
    avg_payout = float(payout_metrics[1] or 0.0)

    current_signal = _clamp((current_rainfall / 75.0) * 0.55 + (current_aqi / 250.0) * 0.45)
    forecast_signal = _clamp((forecast_rainfall / 120.0) * 0.55 + (forecast_aqi / 250.0) * 0.45)
    historical_signal = _clamp(
        (event_count / 24.0) * 0.35
        + (high_severity_count / 12.0) * 0.25
        + (avg_rainfall / 80.0) * 0.20
        + (avg_aqi / 220.0) * 0.10
        + (avg_payout / 250.0) * 0.10
    )
    exposure_signal = _clamp((active_workers / 50.0) * 0.6 + (payout_count / 20.0) * 0.4)

    return round(
        _clamp(0.10 + (current_signal * 0.35) + (forecast_signal * 0.25) + (historical_signal * 0.25) + (exposure_signal * 0.15)),
        4,
    )


def build_admin_forecast(
    db: Session,
    threshold: float,
    location: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> list[dict]:
    context = get_primary_location_context(db=db, location=location, lat=lat, lon=lon)
    snapshot = fetch_weather_snapshot(context.lat, context.lon)
    threshold = max(threshold, 1.0)

    if not snapshot.forecast:
        return []

    premium_base = db.scalar(select(func.avg(PolicyDB.premium)).where(PolicyDB.status == "active")) or 20.0
    predicted_workers = max(context.active_workers, 1)

    results: list[dict] = []
    for point in snapshot.forecast[:7]:
        forecast_risk = estimate_location_risk(
            db=db,
            location=context.location,
            current_rainfall=snapshot.current_rainfall,
            current_aqi=snapshot.current_aqi,
            forecast_rainfall=point.rainfall,
            forecast_aqi=point.aqi,
        )
        trigger_pressure = max(point.rainfall / threshold, point.aqi / 200.0)
        workers_at_risk = min(predicted_workers, max(1, ceil(predicted_workers * min(trigger_pressure, 1.0))))
        expected_loss = round(workers_at_risk * premium_base * forecast_risk * max(trigger_pressure, 0.25), 2)
        results.append(
            {
                "day": point.label,
                "expected_loss": expected_loss,
                "workers_at_risk": workers_at_risk,
                "rainfall": round(point.rainfall, 2),
                "aqi": round(point.aqi, 2),
                "location": context.location,
            }
        )
    return results


def build_admin_stats(
    db: Session,
    threshold: float = 50.0,
    location: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> AdminStatsSnapshot:
    now = datetime.now(timezone.utc)
    active_window = (
        PolicyDB.status == "active",
        PolicyDB.start_date <= now,
        PolicyDB.end_date >= now,
    )

    workers_protected = int(
        db.scalar(
            select(func.count())
            .select_from(PolicyDB)
            .where(*active_window)
        ) or 0
    )

    protected_earnings = float(
        db.scalar(
            select(func.sum(WorkerDB.income * 7.0))
            .select_from(WorkerDB)
            .join(PolicyDB, PolicyDB.worker_id == WorkerDB.id)
            .where(*active_window, WorkerDB.active.is_(True))
        ) or 0.0
    )

    total_premiums = float(
        db.scalar(
            select(func.sum(PolicyDB.premium)).where(*active_window)
        ) or 0.0
    )
    total_payouts = float(
        db.scalar(select(func.sum(PayoutDB.amount)).where(PayoutDB.is_flagged.is_(False))) or 0.0
    )
    ratio = round((total_payouts / total_premiums), 2) if total_premiums > 0 else 0.0
    loss_ratio_percent = round(ratio * 100.0, 2) if total_premiums > 0 else 0.0

    fraud_savings = float(
        db.scalar(select(func.sum(PayoutDB.amount)).where(PayoutDB.is_flagged.is_(True))) or 0.0
    )

    if db.bind.dialect.name == "postgresql":
        avg_seconds = db.scalar(
            select(
                func.avg(
                    func.extract("epoch", PayoutDB.created_at) - func.extract("epoch", EventDB.timestamp)
                )
            )
            .select_from(PayoutDB)
            .join(EventDB, EventDB.id == PayoutDB.event_id)
            .where(PayoutDB.is_flagged.is_(False))
        )
    else:
        avg_seconds = db.scalar(
            select(
                func.avg((func.julianday(PayoutDB.created_at) - func.julianday(EventDB.timestamp)) * 86400.0)
            )
            .select_from(PayoutDB)
            .join(EventDB, EventDB.id == PayoutDB.event_id)
            .where(PayoutDB.is_flagged.is_(False))
        )
    avg_payout_time = f"{round(float(avg_seconds), 2)}s" if avg_seconds is not None else "No payouts yet"

    forecast = build_admin_forecast(db=db, threshold=threshold, location=location, lat=lat, lon=lon)
    predicted_next_week_claims = int(sum(item["workers_at_risk"] for item in forecast))
    predicted_next_week_loss = round(sum(item["expected_loss"] for item in forecast), 2)
    highest_risk_day = max(forecast, key=lambda item: item["expected_loss"])["day"] if forecast else None
    forecast_location = forecast[0]["location"] if forecast else location

    return AdminStatsSnapshot(
        total_workers_protected=workers_protected,
        active_weekly_coverage=workers_protected,
        protected_earnings_estimate=round(protected_earnings, 2),
        claims_premium_ratio=ratio,
        loss_ratio_percent=loss_ratio_percent,
        fraud_savings=round(fraud_savings, 2),
        avg_payout_time=avg_payout_time,
        predicted_next_week_claims=predicted_next_week_claims,
        predicted_next_week_loss=predicted_next_week_loss,
        highest_risk_day=highest_risk_day,
        forecast_location=forecast_location,
        weather_unavailable=not bool(forecast),
    )
