from __future__ import annotations

from typing import List


def preprocess_features(
    rainfall: float,
    aqi: float,
    temperature: float,
    peak: bool,
    location_risk: float,
) -> List[float]:
    # Normalize raw values for stable model behavior.
    rainfall_n = min(rainfall / 200.0, 1.0)
    aqi_n = min(aqi / 500.0, 1.0)
    temp_n = min(max((temperature - 10.0) / 35.0, 0.0), 1.0)
    peak_n = 1.0 if peak else 0.0
    loc_n = min(max(location_risk, 0.0), 1.0)
    return [rainfall_n, aqi_n, temp_n, peak_n, loc_n]
