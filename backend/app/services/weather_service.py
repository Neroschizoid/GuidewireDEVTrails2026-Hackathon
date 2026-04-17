from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import httpx
import time


# =========================
# CACHE + LOCK
# =========================
_weather_cache = {}
_inflight = {}
CACHE_TTL = 300


# =========================
# DATA MODELS
# =========================
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

    forecast: List[ForecastPoint]

    available: bool = True
    error: Optional[str] = None


# =========================
# UTIL
# =========================
def get_peak_hour() -> int:
    hour = datetime.now().hour
    return 1 if (8 <= hour <= 11 or 17 <= hour <= 22) else 0


def geocode_location(location: str) -> tuple[float, float]:
    try:
        r = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": location,
                "count": 1,
                "language": "en",
                "format": "json"
            },
            timeout=10.0
        )

        r.raise_for_status()

        results = r.json().get("results", [])

        if results:
            item = results[0]
            return (
                float(item["latitude"]),
                float(item["longitude"])
            )

    except Exception as e:
        print(f"Geocoding Error: {e}")

    return 28.49615, 77.53601


# =========================
# MAIN
# =========================
def fetch_weather_snapshot(lat: float, lon: float) -> WeatherSnapshot:

    key = f"{round(lat,1)},{round(lon,1)}"
    now = time.time()

    # CACHE
    if key in _weather_cache:
        cached = _weather_cache[key]
        if now - cached["time"] < CACHE_TTL:
            return cached["data"]

    # PREVENT PARALLEL DUPLICATES
    if key in _inflight:
        return _weather_cache.get(key, {}).get(
            "data",
            WeatherSnapshot(
                0.0,50.0,50.0,25.0,
                0.0,50.0,[],
                False,"In progress"
            )
        )

    _inflight[key] = True

    try:

        # ====================================
        # FULL WEATHER URL (CURRENT + HOURLY)
        # ====================================

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}"
            f"&longitude={lon}"
            f"&current=precipitation,temperature_2m"
            f"&hourly=precipitation,temperature_2m"
            f"&timezone=auto"
            f"&forecast_days=7"
        )

        weather_res = httpx.get(weather_url, timeout=10.0)
        weather_data = weather_res.json()


        # ====================================
        # FULL AQI URL (CURRENT + HOURLY)
        # ====================================

        aqi_url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}"
            f"&longitude={lon}"
            f"&current=european_aqi"
            f"&hourly=european_aqi"
            f"&timezone=auto"
            f"&forecast_days=7"
        )

        aqi_res = httpx.get(aqi_url, timeout=10.0)
        air_data = aqi_res.json()


        # ====================================
        # CURRENT VALUES
        # ====================================

        rainfall = float(
            weather_data.get("current", {})
            .get("precipitation", 0.0)
        )

        temp = float(
            weather_data.get("current", {})
            .get("temperature_2m", 25.0)
        )

        aqi = float(
            air_data.get("current", {})
            .get("european_aqi", 50.0)
        )


        # ====================================
        # DYNAMIC 24H RAINFALL
        # ====================================

        hourly_precip = (
            weather_data.get("hourly", {})
            .get("precipitation", [])
        )

        next_24h_rainfall = sum(
            float(x or 0.0)
            for x in hourly_precip[:24]
        )


        # ====================================
        # DYNAMIC 24H PEAK AQI
        # ====================================

        hourly_aqi = (
            air_data.get("hourly", {})
            .get("european_aqi", [])
        )

        next_24h_peak_aqi = max(
            (float(x or 0.0) for x in hourly_aqi[:24]),
            default=aqi
        )


        # ====================================
        # BUILD FORECAST ARRAY
        # ====================================

        forecast = []

        times = (
            weather_data.get("hourly", {})
            .get("time", [])
        )

        temps = (
            weather_data.get("hourly", {})
            .get("temperature_2m", [])
        )

        limit = min(
            24,
            len(times),
            len(hourly_precip),
            len(temps),
            len(hourly_aqi)
        )

        for i in range(limit):

            forecast.append(
                ForecastPoint(
                    label=f"H+{i}",
                    timestamp=times[i],
                    rainfall=float(hourly_precip[i] or 0.0),
                    aqi=float(hourly_aqi[i] or 0.0),
                    temperature=float(temps[i] or 25.0),
                )
            )


        # ====================================
        # FINAL RESPONSE
        # ====================================

        result = WeatherSnapshot(
            current_rainfall=rainfall,
            current_aqi=aqi,
            current_us_aqi=aqi,
            current_temperature=temp,

            next_24h_rainfall=next_24h_rainfall,
            next_24h_peak_aqi=next_24h_peak_aqi,

            forecast=forecast,

            available=True
        )

        _weather_cache[key] = {
            "data": result,
            "time": now
        }

        return result

    except Exception as e:

        print(f"Weather API Error: {e}")

        fallback = WeatherSnapshot(
            0.0,
            50.0,
            50.0,
            25.0,
            0.0,
            50.0,
            [],
            available=False,
            error=str(e)
        )

        _weather_cache[key] = {
            "data": fallback,
            "time": now
        }

        return fallback

    finally:
        _inflight.pop(key, None)


def fetch_live_weather(lat: float, lon: float):
    snap = fetch_weather_snapshot(lat, lon)

    return (
        snap.current_rainfall,
        snap.current_aqi,
        snap.current_temperature
    )
