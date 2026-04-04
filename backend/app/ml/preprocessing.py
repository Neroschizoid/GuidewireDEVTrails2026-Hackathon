from __future__ import annotations

from typing import List


def preprocess_features(
    rainfall: float,
    aqi: float,
    temperature: float,
    peak: bool,
    location_risk: float,
) -> List[float]:
    """
    Normalizes raw values to match the scale used in generate_data.py.
    X features: rainfall, aqi, temperature, peak_hour, location_risk
    """
    # Normalized as per generate_data.py (capped at 1.0 for model stability)
    rainfall_n = min(max(rainfall / 20.0, 0.0), 1.0)
    aqi_n = min(max(aqi / 300.0, 0.0), 1.0)
    temp_n = min(max((temperature - 20.0) / 25.0, 0.0), 1.0)
    peak_n = 1.0 if peak else 0.0
    loc_n = min(max(location_risk, 0.0), 1.0)

    # Return in the order expected by the model: 
    # [rainfall, aqi, temperature, peak_hour, location_risk]
    return [rainfall_n, aqi_n, temp_n, peak_n, loc_n]
