def calculate_premium(risk_score, base_price: float = 20):
    premium = base_price * (1 + risk_score)
    return round(premium, 2)