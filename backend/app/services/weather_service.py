from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
import time

# ✅ CACHE + LOCK
_weather_cache = {}
_inflight_requests = {}
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
    return 1 if (8 <= hour <= 11 or 17 <= hour <= 22) else 0


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


def _get_json_with_retry(url: str, params: dict, attempts: int = 2) -> dict:
    for attempt in range(attempts):
        try:
            response = httpx.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            if attempt == attempts - 1:
                raise exc
            time.sleep(1 + attempt)  # ✅ controlled retry


def fetch_weather_snapshot(lat: float, lon: float) -> WeatherSnapshot:
    # ✅ rounded key (VERY IMPORTANT)
    key = f"{round(lat,1)},{round(lon,1)}"
    now = time.time()

    # ✅ CACHE HIT
    if key in _weather_cache:
        cached = _weather_cache[key]
        if now - cached["time"] < CACHE_TTL:
            return cached["data"]

    # 🔥 PREVENT PARALLEL CALLS
    if key in _inflight_requests:
        return _weather_cache.get(key, {}).get("data", WeatherSnapshot(
            current_rainfall=0.0,
            current_aqi=0.0,
            current_us_aqi=0.0,
            current_temperature=25.0,
            next_24h_rainfall=0.0,
            next_24h_peak_aqi=0.0,
            forecast=[],
            available=False,
            error="Request already in progress"
        ))

    _inflight_requests[key] = True

    try:
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

        errors = []

        try:
            weather_data = _get_json_with_retry(OPEN_METEO_WEATHER_URL, weather_params)
        except Exception as e:
            weather_data = {}
            errors.append(str(e))

        try:
            air_data = _get_json_with_retry(OPEN_METEO_AIR_URL, air_params)
        except Exception as e:
            air_data = {}
            errors.append(str(e))

        if not weather_data and not air_data:
            result = WeatherSnapshot(
                current_rainfall=0.0,
                current_aqi=50.0,
                current_us_aqi=50.0,
                current_temperature=25.0,
                next_24h_rainfall=0.0,
                next_24h_peak_aqi=50.0,
                forecast=[],
                available=False,
                error="; ".join(errors),
            )
            _weather_cache[key] = {"data": result, "time": now}
            return result

        rainfall = float(weather_data.get("current", {}).get("precipitation", 0.0) or 0.0)
        temp = float(weather_data.get("current", {}).get("temperature_2m", 25.0) or 25.0)

        current_air = air_data.get("current", {}) or {}
        aqi = float(current_air.get("european_aqi", 50.0) or 50.0)

        result = WeatherSnapshot(
            current_rainfall=rainfall,
            current_aqi=aqi,
            current_us_aqi=aqi,
            current_temperature=temp,
            next_24h_rainfall=0.0,
            next_24h_peak_aqi=aqi,
            forecast=[],
            available=True,
        )

        _weather_cache[key] = {"data": result, "time": now}
        return result

    finally:
        # ✅ ALWAYS CLEAN LOCK
        _inflight_requests.pop(key, None)


def fetch_live_weather(lat: float, lon: float) -> tuple[float, float, float]:
    snapshot = fetch_weather_snapshot(lat, lon)
    return snapshot.current_rainfall, snapshot.current_aqi, snapshot.current_temperature
