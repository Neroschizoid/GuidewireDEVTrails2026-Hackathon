import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.weather_service import fetch_live_weather, get_peak_hour
from app.ml.inference import run_inference
from app.ml.model_loader import load_model

def test_risk_flow_integration():
    print("--- 1. Testing Weather Service ---")
    lat, lon = 12.9716, 77.5946
    rainfall, aqi, temp = fetch_live_weather(lat, lon)
    print(f"Rainfall: {rainfall} mm")
    print(f"AQI: {aqi}")
    print(f"Temperature: {temp} °C")
    
    assert isinstance(rainfall, (float, int))
    assert isinstance(aqi, (float, int))
    assert isinstance(temp, (float, int))

    print("\n--- 2. Testing Peak Hour Logic ---")
    peak = get_peak_hour()
    now_hour = datetime.now().hour
    print(f"Current Hour: {now_hour}")
    print(f"Peak Status: {peak}")
    
    if 8 <= now_hour <= 11 or 17 <= now_hour <= 22:
        assert peak == 1
    else:
        assert peak == 0

    print("\n--- 3. Testing ML Inference ---")
    # All 5 features used for training: rain, aqi, temp, peak, loc
    # Plus income, hours for the output calculation
    output = run_inference(
        rainfall=rainfall,
        aqi=aqi,
        temperature=temp,
        peak=bool(peak),
        location_risk=0.6,
        income=1500,
        hours=8,
        base_price=20.0
    )
    
    print(f"Risk Score: {output.risk_score}")
    print(f"Premium Quote: {output.premium_quote}")
    print(f"Estimated Loss: {output.estimated_loss}")
    
    assert 0.0 <= output.risk_score <= 1.0
    assert output.premium_quote > 0
    assert output.estimated_loss >= 0

    print("\n✅ ALL PARAMETERS CONFIRMED & MODEL IS OPERATIONAL")

if __name__ == "__main__":
    try:
        test_risk_flow_integration()
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        sys.exit(1)
