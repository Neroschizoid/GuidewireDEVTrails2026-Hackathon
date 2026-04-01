from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class SimpleRiskModel:
    # Weight order: rainfall, aqi, temperature, peak, location_risk
    weights: List[float] = (0.35, 0.25, 0.10, 0.10, 0.20)

    def predict(self, features: List[float]) -> float:
        score = sum(w * f for w, f in zip(self.weights, features))
        return min(max(score, 0.0), 1.0)


def load_model() -> SimpleRiskModel:
    return SimpleRiskModel()
