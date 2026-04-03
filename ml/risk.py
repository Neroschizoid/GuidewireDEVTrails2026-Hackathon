def calculate_risk(rainfall, aqi, peak, location="normal"):
    risk = 0.0

    # Rain impact
    if rainfall > 50:
        risk += 0.4
    elif rainfall > 20:
        risk += 0.2

    # AQI impact
    if aqi > 300:
        risk += 0.3
    elif aqi > 150:
        risk += 0.15

    # Peak hours impact
    if peak:
        risk += 0.2

    # Location-based risk (hyper-local)
    if location == "high_risk":
        risk += 0.1

    return min(risk, 1.0)