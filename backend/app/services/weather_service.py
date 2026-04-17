from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
import time

# ✅ CACHE SETUP
_weather_cache = {}
CACHE_TTL = 300  # 5 minutes

OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


@dataclass
class ForecastPoint:
    label: str
    timestamp: str
    rainfall: float
    aqi: float
    temperature: float


@dataclass
class WeatherSnapshot:
    current_rainfall: float
    current_aqi: float
    current_us_aqi: float
    current_temperature: float
    next_24h_rainfall: float
    next_24h_peak_aqi: float
    forecast: list[ForecastPoint]
    available: bool = True
    error: Optional[str] = None


def get_peak_hour() -> int:
    hour = datetime.now().hour
    if 8 <= hour <= 11 or 17 <= hour <= 22:
        return 1
    return 0


def geocode_location(location: str) -> tuple[float, float]:
    try:
        response = httpx.get(
            OPEN_METEO_GEOCODE_URL,
            params={"name": location, "count": 1, "language": "en", "format": "json"},
            timeout=10.0,
        )
        response.raise_for_status()
        results = response.json().get("results") or []
        if results:
            item = results[0]
            return float(item["latitude"]), float(item["longitude"])
    except Exception as exc:
        print(f"Geocoding Error: {exc}")

    return 12.9716, 77.5946


def _get_json_with_retry(url: str, params: dict, attempts: int = 3) -> dict:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = httpx.get(url, params=params, timeout=10.0 + (attempt * 5.0))
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            time.sleep(2 ** attempt)  # ✅ backoff added
    if last_error is not None:
        raise last_error
    raise RuntimeError("Weather API request failed without an error.")


def fetch_weather_snapshot(lat: float, lon: float) -> WeatherSnapshot:
    key = f"{lat},{lon}"
    now = time.time()

    # ✅ RETURN FROM CACHE
    if key in _weather_cache:
        cached = _weather_cache[key]
        if now - cached["time"] < CACHE_TTL:
            return cached["data"]

    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "precipitation,temperature_2m",
        "hourly": "precipitation,temperature_2m",
        "timezone": "auto",
        "forecast_days": 7,
    }

    air_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "european_aqi,us_aqi,pm2_5",
        "hourly": "european_aqi,us_aqi,pm2_5",
        "timezone": "auto",
        "forecast_days": 7,
    }

    weather_data: dict = {}
    air_data: dict = {}
    errors: list[str] = []

    try:
        weather_data = _get_json_with_retry(OPEN_METEO_WEATHER_URL, weather_params)
    except Exception as exc:
        errors.append(f"weather feed unavailable: {exc}")

    try:
        air_data = _get_json_with_retry(OPEN_METEO_AIR_URL, air_params)
    except Exception as exc:
        errors.append(f"air quality feed unavailable: {exc}")

    if not weather_data and not air_data:
        error_message = "; ".join(errors) or "Weather feeds unavailable"
        print(f"Weather API Error: {error_message}")
        result = WeatherSnapshot(
            current_rainfall=0.0,
            current_aqi=0.0,
            current_us_aqi=0.0,
            current_temperature=25.0,
            next_24h_rainfall=0.0,
            next_24h_peak_aqi=0.0,
            forecast=[],
            available=False,
            error=error_message,
        )
        _weather_cache[key] = {"data": result, "time": now}
        return result

    rainfall = float(weather_data.get("current", {}).get("precipitation", 0.0) or 0.0)
    temp = float(weather_data.get("current", {}).get("temperature_2m", 25.0) or 25.0)

    current_air = air_data.get("current", {}) or {}
    aqi_eu = float(current_air.get("european_aqi", 0.0) or 0.0)
    aqi_us = float(current_air.get("us_aqi", 0.0) or 0.0)
    pm25 = float(current_air.get("pm2_5", 0.0) or 0.0)
    aqi = max(aqi_eu, aqi_us, pm25 * 4.0)

    weather_hourly = weather_data.get("hourly", {}) or {}
    air_hourly = air_data.get("hourly", {}) or {}

    hourly_times = (weather_hourly.get("time", []) or air_hourly.get("time", []) or [])[:24 * 7]
    hourly_rain = weather_hourly.get("precipitation", []) or []
    hourly_temp = weather_hourly.get("temperature_2m", []) or []

    hourly_aqi_eu = air_hourly.get("european_aqi", []) or []
    hourly_aqi_us = air_hourly.get("us_aqi", []) or []
    hourly_pm25 = air_hourly.get("pm2_5", []) or []

    points: list[ForecastPoint] = []

    for idx, timestamp in enumerate(hourly_times):
        point_rainfall = float(hourly_rain[idx]) if idx < len(hourly_rain) and hourly_rain[idx] is not None else 0.0
        point_temp = float(hourly_temp[idx]) if idx < len(hourly_temp) and hourly_temp[idx] is not None else temp

        point_aqi = max(
            float(hourly_aqi_eu[idx]) if idx < len(hourly_aqi_eu) and hourly_aqi_eu[idx] is not None else 0.0,
            float(hourly_aqi_us[idx]) if idx < len(hourly_aqi_us) and hourly_aqi_us[idx] is not None else 0.0,
            (float(hourly_pm25[idx]) * 4.0) if idx < len(hourly_pm25) and hourly_pm25[idx] is not None else 0.0,
        )

        points.append(
            ForecastPoint(
                label=timestamp[5:10],
                timestamp=timestamp,
                rainfall=point_rainfall,
                aqi=point_aqi or aqi,
                temperature=point_temp,
            )
        )

    daily_points: list[ForecastPoint] = []

    for start in range(0, len(points), 24):
        chunk = points[start:start + 24]
        if not chunk:
            continue

        daily_points.append(
            ForecastPoint(
                label=chunk[0].timestamp[5:10],
                timestamp=chunk[0].timestamp,
                rainfall=sum(item.rainfall for item in chunk),
                aqi=max(item.aqi for item in chunk),
                temperature=sum(item.temperature for item in chunk) / len(chunk),
            )
        )

    next_day = points[:24]
    next_24h_rainfall = sum(item.rainfall for item in next_day)
    next_24h_peak_aqi = max((item.aqi for item in next_day), default=aqi)

    partial_error = "; ".join(errors) or None

    result = WeatherSnapshot(
        current_rainfall=rainfall,
        current_aqi=aqi,
        current_us_aqi=aqi_us,
        current_temperature=temp,
        next_24h_rainfall=next_24h_rainfall,
        next_24h_peak_aqi=next_24h_peak_aqi,
        forecast=daily_points,
        available=True,
        error=partial_error,
    )

    # ✅ SAVE TO CACHE
    _weather_cache[key] = {"data": result, "time": now}

    return result


def fetch_live_weather(lat: float, lon: float) -> tuple[float, float, float]:
    snapshot = fetch_weather_snapshot(lat, lon)
    return snapshot.current_rainfall, snapshot.current_aqi, snapshot.current_temperature
