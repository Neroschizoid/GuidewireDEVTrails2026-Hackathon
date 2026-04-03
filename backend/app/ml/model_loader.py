from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, List

try:
    import joblib  # type: ignore
except Exception:  # pragma: no cover
    joblib = None  # type: ignore


@dataclass
class SimpleRiskModel:
    # Weight order: rainfall, aqi, temperature, peak, location_risk
    weights: List[float] = (0.35, 0.25, 0.10, 0.10, 0.20)

    def predict(self, features: List[float]) -> float:
        score = sum(w * f for w, f in zip(self.weights, features))
        return min(max(score, 0.0), 1.0)


@dataclass
class LoadedRiskModel:
    model: Any

    def predict(self, features: List[float]) -> float:
        """
        Supports common sklearn-like estimators:
        - predict(X) where X is [features]
        - returns scalar or array-like
        """
        pred = None
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


def load_model() -> SimpleRiskModel:
    model_path = os.getenv("MODEL_PATH")
    if model_path and os.path.exists(model_path):
        if joblib is None:
            return SimpleRiskModel()
        loaded = joblib.load(model_path)
        return LoadedRiskModel(model=loaded)

    return SimpleRiskModel()
