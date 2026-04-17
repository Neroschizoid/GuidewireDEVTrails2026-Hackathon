from datetime import datetime
import httpx
import time

# ✅ cache + lock
_weather_cache = {}
_inflight = {}
CACHE_TTL = 300  # 5 minutes


def get_peak_hour() -> int:
    hour = datetime.now().hour
    return 1 if (8 <= hour <= 11 or 17 <= hour <= 22) else 0


def fetch_live_weather(lat: float, lon: float) -> tuple[float, float, float]:
    # ✅ normalized key (fix precision issue)
    key = f"{round(lat,1)},{round(lon,1)}"
    now = time.time()

    # ✅ return cached result
    if key in _weather_cache:
        cached = _weather_cache[key]
        if now - cached["time"] < CACHE_TTL:
            return cached["data"]

    # 🔥 prevent multiple parallel calls
    if key in _inflight:
        return _weather_cache.get(key, {}).get("data", (0.0, 50.0, 25.0))

    _inflight[key] = True

    try:
        # 🌦 Weather API
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=precipitation,temperature_2m&timezone=auto"
        )

        weather_res = httpx.get(weather_url, timeout=10.0)
        weather_data = weather_res.json()

        rainfall = weather_data.get("current", {}).get("precipitation", 0.0)
        temp = weather_data.get("current", {}).get("temperature_2m", 25.0)

        # 🌫 AQI API
        aqi_url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lon}"
            f"&current=european_aqi&timezone=auto"
        )

        aqi_res = httpx.get(aqi_url, timeout=10.0)
        aqi_data = aqi_res.json()

        aqi = aqi_data.get("current", {}).get("european_aqi", 50.0)

        result = (float(rainfall), float(aqi), float(temp))

        # ✅ store cache
        _weather_cache[key] = {
            "data": result,
            "time": now
        }

        return result

    except Exception as e:
        print(f"Weather API Error: {e}")

        # ✅ fallback to cached if available
        if key in _weather_cache:
            return _weather_cache[key]["data"]

        return 0.0, 50.0, 25.0

    finally:
        # ✅ always release lock
        _inflight.pop(key, None)
