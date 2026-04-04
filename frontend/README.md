# Frontend — Parametric Shield UI

React 18 + Vite mobile-first PWA for Gig Worker parametric insurance. Communicates with the FastAPI backend via JWT-authenticated API calls with automatic silent token refresh.

---

## Quick Start

```bash
npm install
npm run dev
```

App runs at `http://localhost:5173`. Backend must be running at `http://localhost:8000`.

---

## Environment Variables

Create `frontend/.env` (optional — defaults to localhost):

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## App Structure

```
src/
├── GWApp.jsx     # Main application — all tabs, state management, API calls
├── api.js        # HTTP layer — JWT injection, silent refresh, session expiry
├── index.css     # Global design system (neon / midnight themes)
└── main.jsx      # React entry point
```

---

## Authentication Flow

On login/register, the backend returns an `access_token` (15min) and `refresh_token` (7d). Both are stored in `localStorage` under `gw_worker_auth_v1`.

`api.js` automatically:
1. Attaches `Authorization: Bearer <access_token>` to every request
2. On `401 Unauthorized`, calls `/api/v1/workers/refresh` silently
3. On successful refresh, retries the original request
4. If refresh also fails → dispatches `gw:session_expired` → app auto-logs out with an error message

---

## Tabs

| Tab | Description |
|-----|-------------|
| **Dashboard** | ML risk score, live coords, upgrade path, weekly earnings progress |
| **Tracker** | Online/Offline toggle, parametric trigger button, payout display |
| **Store** | Shield tier selection with upgrade/renew; pro-rated pricing |
| **Account** | Profile, total secured earnings, active tier, logout |

---

## Key UX Logic

- **"Go to Policy Store"** only appears on Dashboard if ML risk recommends a higher tier than the worker currently holds
- **Activate Trigger** is unlocked only when `auth.active_policy === true` (server-validated 7-day window)
- **Store tiers** below the active shield are dimmed/disabled; active tier shows "Active Tier" or "Expired — Renew"
- **Weekly earnings** update instantly on the UI after a successful payout (`po.amount > 0 && ev.type !== "none"`)
- **Total Secured** is sourced from the backend (`auth.weekly_earnings`) — survives page reloads and logout/login

---

## Themes

Toggle between **Neon** and **Midnight** themes via the top-right Theme button. Preference is persisted in `localStorage`.
