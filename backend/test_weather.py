import sys
from app.services.weather_service import fetch_live_weather

try:
    rain, aqi, temp = fetch_live_weather(12.9716, 77.5946)
    print(f"Rain: {rain}, AQI: {aqi}, Temp: {temp}")
except Exception as e:
    print(f"Error: {e}")
