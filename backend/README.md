# Backend — Parametric Shield API

FastAPI backend for the Gig Worker Parametric Insurance platform. Handles ML risk scoring, live weather integration, JWT authentication, parametric event triggers, and idempotent payout processing.

---

## Quick Start

```bash
conda activate gw
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs auto-generated at: `http://localhost:8000/docs`

---

## Environment Variables

Create `backend/.env`:

```env
DATABASE_URL=postgresql://user:pass@host:port/dbname
SECRET_KEY=your_random_secret_key_here
```

`SECRET_KEY` is used for JWT signing. Generate one with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Authentication

All endpoints except `/register`, `/login`, and `/refresh` are JWT-protected.

```
POST /api/v1/workers/login
→ { access_token, refresh_token, worker_id, shield, active_policy, weekly_earnings, ... }

POST /api/v1/workers/refresh
Body: { refresh_token }
→ { access_token }
```

Include in all subsequent requests:
```
Authorization: Bearer <access_token>
```

| Token | Lifetime |
|-------|----------|
| Access Token | 15 minutes |
| Refresh Token | 7 days |

---

## Endpoints

### Workers (Public)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/workers/register` | Register with name, email, password, location, income |
| POST | `/api/v1/workers/login` | Login → JWT pair + weekly_earnings + active_policy |
| POST | `/api/v1/workers/refresh` | Exchange refresh token for new access token |
| GET | `/api/v1/workers/{id}` | Get worker profile (JWT required) |

### Risk (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/risk/calculate` | Run ML model with live Open-Meteo weather |

### Payment (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/payment/process` | Buy/upgrade shield tier → auto-creates 7-day policy |

### Events & Payouts (JWT required)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/event/trigger` | Detect weather event + issue payouts to all active workers |
| POST | `/api/v1/payout/process` | Process single payout (idempotent — safe to retry) |

---

## Services Overview

| Service | Purpose |
|---------|---------|
| `weather_service.py` | Calls Open-Meteo API for `rainfall` + `AQI` from lat/lon |
| `risk_service.py` | Loads scikit-learn model → computes risk, premium, estimated loss |
| `event_service.py` | Infers event type (rain/pollution/none), loops over workers, triggers payouts |
| `payout_service.py` | Idempotency engine — blocks duplicate payouts via DB unique constraint |
| `validation_service.py` | Checks worker activity, policy validity (7-day window), location match |

---

## Parametric Trigger Logic

```
rainfall >= 50 mm  →  "rain" event
AQI >= 300         →  "pollution" event
otherwise          →  "none" (no payout)

severity = "high"  if rainfall >= 80 or AQI >= 400
           "medium" otherwise

payout_amount = max((rainfall * 1.2) + (aqi * 0.2), 0.0)
```

---

## Running Tests

```bash
conda activate gw
pytest tests/ -v
```

Tests use mock weather injection for deterministic event results. No live API calls during tests.

---

## Database Setup

Ensure your Supabase project has the following tables. Migrations can be applied by running:

```bash
python -c "from app.core.db import Base, engine; Base.metadata.create_all(engine)"
```

Tables:
- `workers` — includes `shield` FK to `shields.p_id`
- `shields` — seed with 4 rows: (0, No Shield), (1, Basic), (2, Pro), (3, Elite)
- `policies` — auto-created on `/payment/process`
- `events`, `payouts`, `risk_profiles`
