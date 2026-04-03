import pandas as pd
import random

data = []

for _ in range(80):
    rainfall = random.randint(0, 100)
    aqi = random.randint(50, 500)
    temperature = random.randint(20, 40)
    peak = random.randint(0, 1)
    location_risk = round(random.uniform(0, 1), 2)

    risk = (
        0.4 * (rainfall / 100) +
        0.3 * (aqi / 500) +
        0.2 * peak +
        0.1 * location_risk
    )

    risk = min(round(risk, 2), 1.0)

    data.append([
        rainfall, aqi, temperature, peak, location_risk, risk
    ])

df = pd.DataFrame(data, columns=[
    "rainfall", "aqi", "temperature", "peak_hour", "location_risk", "risk_score"
])

df.to_csv("data.csv", index=False)

print("Dataset generated successfully ")