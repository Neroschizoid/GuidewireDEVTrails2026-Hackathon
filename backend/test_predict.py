from app.ml.inference import run_inference

result = run_inference(
    rainfall=15.0,
    aqi=150.0,
    temperature=35.0,
    peak=True,
    location_risk=0.5,
    income=500.0,
    hours=8.0
)

print("--- ML Prediction Results ---")
print(f"Risk Score:     {result.risk_score}")
print(f"Premium Quote:  {result.premium_quote}")
print(f"Estimated Loss: {result.estimated_loss}")
print(f"Fraud Flag:     {result.fraud_flag}")
