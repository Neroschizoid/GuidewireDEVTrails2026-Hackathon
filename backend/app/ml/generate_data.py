import random
import pandas as pd

data = []

for _ in range(1000):
    rainfall = random.uniform(0, 20)          # mm
    aqi = random.uniform(20, 300)             # AQI scale
    temperature = random.uniform(20, 45)      # °C
    peak_hour = random.choice([0, 1])         # binary
    location_risk = random.uniform(0.3, 0.8)  # zone risk

    # normalized values
    rain_n = rainfall / 20
    aqi_n = aqi / 300
    temp_n = (temperature - 20) / 25

    # weighted realistic risk formula
    risk = (
        0.35 * rain_n +
        0.30 * aqi_n +
        0.15 * temp_n +
        0.10 * peak_hour +
        0.10 * location_risk
    )

    # clamp between 0–1
    risk = max(0, min(risk, 1))

    data.append([
        rainfall, aqi, temperature,
        peak_hour, location_risk, risk
    ])

df = pd.DataFrame(data, columns=[
    "rainfall", "aqi", "temperature",
    "peak_hour", "location_risk", "risk_score"
])

df.to_csv("ml/data.csv", index=False)

print("✅ data.csv generated with 1000 rows")