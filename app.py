from flask import Flask, request, jsonify
import uuid
import requests
import random
import os

app = Flask(__name__)

# ---------------- CONFIG ----------------
ML_API = os.getenv("ML_API", "http://127.0.0.1:8000/predict")

# ---------------- MOCK DB ----------------
users = {}
policies = {}
payouts = set()

# ---------------- HOME ----------------
@app.route('/')
def home():
    return "Backend (ML-ready) running 🚀"

# ---------------- REGISTER ----------------
@app.route('/register', methods=['POST'])
def register():
    data = request.json

    user_id = str(uuid.uuid4())

    users[user_id] = {
        "name": data.get("name"),
        "location": data.get("location"),
        "income": data.get("income", 100)
    }

    return jsonify({"user_id": user_id})

# ---------------- ENV DATA ----------------
def get_env_data(location):
    # Replace with real APIs later
    return {
        "rainfall": random.randint(30, 100),
        "aqi": random.randint(100, 400),
        "temperature": random.randint(20, 40)
    }

# ---------------- ML CALL ----------------
def call_ml(payload):
    try:
        res = requests.post(ML_API, json=payload, timeout=2)
        return res.json()
    except:
        # 🔥 FALLBACK (if ML not running)
        return {
            "risk_score": round(payload["rainfall"]/100, 2),
            "weekly_premium": int(payload["rainfall"] * 2),
            "estimated_loss": int(payload["income"] * (payload["rainfall"]/50)),
            "fraud_flag": random.choice([False, False, False, True])
        }

# ---------------- ANALYZE ----------------
@app.route('/analyze/<user_id>', methods=['GET'])
def analyze(user_id):

    if user_id not in users:
        return jsonify({"error": "User not found"}), 404

    user = users[user_id]
    env = get_env_data(user["location"])

    payload = {
        **env,
        "peak": True,
        "location_risk": 0.8,
        "income": user["income"],
        "hours": 2,
        "active": True,
        "paid": False
    }

    ml = call_ml(payload)

    # Store policy
    policies[user_id] = {
        "active": True,
        "premium": ml["weekly_premium"],
        "risk": ml["risk_score"]
    }

    return jsonify({
        "risk": ml["risk_score"],
        "premium": ml["weekly_premium"],
        "loss": ml["estimated_loss"],
        "fraud": ml["fraud_flag"]
    })

# ---------------- TRIGGER + PAYOUT ----------------
@app.route('/trigger', methods=['POST'])
def trigger():

    data = request.json
    location = data.get("location")
    event_id = str(uuid.uuid4())

    results = []

    for user_id, user in users.items():

        # location match
        if user["location"] != location:
            continue

        # policy check
        if user_id not in policies or not policies[user_id]["active"]:
            continue

        env = get_env_data(location)

        payload = {
            **env,
            "peak": True,
            "location_risk": 0.8,
            "income": user["income"],
            "hours": 2,
            "active": True,
            "paid": False
        }

        ml = call_ml(payload)

        # fraud check
        if ml["fraud_flag"]:
            results.append({
                "user_id": user_id,
                "status": "rejected (fraud)"
            })
            continue

        # idempotency (no duplicate payout)
        if (user_id, event_id) in payouts:
            continue

        payout = ml["estimated_loss"]

        payouts.add((user_id, event_id))

        results.append({
            "user_id": user_id,
            "payout": payout
        })

    return jsonify({
        "event_id": event_id,
        "results": results
    })

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)