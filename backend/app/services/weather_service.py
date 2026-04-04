from __future__ import annotations

import httpx

def fetch_live_weather(lat: float, lon: float) -> tuple[float, float]:
    """
    Fetches real-time weather and air quality from Open-Meteo.
    Returns (rainfall_mm, aqi).
    """
    try:
        # Weather API for precipitation
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=precipitation&timezone=auto"
        weather_res = httpx.get(weather_url, timeout=10.0)
        weather_data = weather_res.json()
        rainfall = weather_data.get("current", {}).get("precipitation", 0.0)

        # Air Quality API for European AQI
        aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=european_aqi&timezone=auto"
        aqi_res = httpx.get(aqi_url, timeout=10.0)
        aqi_data = aqi_res.json()
        aqi = aqi_data.get("current", {}).get("european_aqi", 20.0)

        return float(rainfall), float(aqi)
    except Exception as e:
        print(f"Weather API Error: {e}")
        # Default fallback values if the API fails
        return 0.0, 50.0
