from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, List

from dotenv import load_dotenv

try:
    import joblib  # type: ignore
except Exception:  # pragma: no cover
    joblib = None  # type: ignore

load_dotenv()


@dataclass
class SimpleRiskModel:
    # Weight order: [rainfall, aqi, temperature, peak, location_risk]
    # Updated to match the current training formula:
    # 0.35 rain + 0.3 aqi + 0.15 temp + 0.1 peak + 0.1 loc
    weights: List[float] = (0.35, 0.30, 0.15, 0.10, 0.10)

    def predict(self, features: List[float]) -> float:
        score = sum(w * f for w, f in zip(self.weights, features))
        return min(max(score, 0.0), 1.0)


@dataclass
class LoadedRiskModel:
    model: Any

    def predict(self, features: List[float]) -> float:
        """
        Supports common sklearn-like estimators.
        Passes a DataFrame with feature names to avoid 'fitted with feature names' warnings.
        """
        try:
            import pandas as pd
            # Column names must match those in train_model.py
            cols = ["rainfall", "aqi", "temperature", "peak_hour", "location_risk"]
            df = pd.DataFrame([features], columns=cols)
            pred = self.model.predict(df)
        except Exception:
            # Fallback for simple models or if pandas is unavailable
            try:
                pred = self.model.predict([features])
            except Exception:
                pred = self.model.predict(features)

        if isinstance(pred, (list, tuple)):
            pred = pred[0]

        # numpy scalar/array conversion
        try:
            if hasattr(pred, "item"):
                pred = pred.item()
        except Exception:
            pass

        score = float(pred)
        return max(0.0, min(score, 1.0))


# Cache for the loaded model to avoid file I/O on every request
_CACHED_MODEL: Any = None

def load_model() -> SimpleRiskModel | LoadedRiskModel:
    global _CACHED_MODEL
    if _CACHED_MODEL is not None:
        return _CACHED_MODEL

    model_path = os.getenv("MODEL_PATH")
    if model_path and os.path.exists(model_path):
        if joblib is None:
            print("⚠️ joblib not installed. Falling back to SimpleRiskModel.")
            return SimpleRiskModel()
        try:
            loaded = joblib.load(model_path)
            print(f"✅ Loaded ML Model from: {model_path}")
            _CACHED_MODEL = LoadedRiskModel(model=loaded)
            return _CACHED_MODEL
        except Exception as e:
            print(f"❌ Error loading model from {model_path}: {e}")
            return SimpleRiskModel()

    print("⚠️ MODEL_PATH not found. Using SimpleRiskModel fallback.")
    return SimpleRiskModel()
