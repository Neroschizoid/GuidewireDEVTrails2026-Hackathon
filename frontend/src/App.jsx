import React, { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "./api";

function Money({ value }) {
  if (value === null || value === undefined) return <span className="hint">—</span>;
  return <span>{Number(value).toFixed(2)}</span>;
}

function StatusBox({ kind, children }) {
  const cls = kind ? `alert ${kind}` : "alert";
  return <div className={cls}>{children}</div>;
}

export default function App() {
  const [apiStatus, setApiStatus] = useState(null);
  const [error, setError] = useState(null);

  const [workerForm, setWorkerForm] = useState({
    name: "",
    email: "",
    password: "",
    location: "",
    income: 1000,
  });
  const [workerId, setWorkerId] = useState("");

  const [riskForm, setRiskForm] = useState({
    rainfall: 80,
    aqi: 250,
    temperature: 28,
    peak: true,
    location_risk: 0.5,
    hours: 2,
    worker_id: "",
  });
  const [riskResult, setRiskResult] = useState(null);

  const [policyForm, setPolicyForm] = useState({
    worker_id: "",
    base_price: 20,
    days: 7,
  });
  const [policyResult, setPolicyResult] = useState(null);

  const [eventForm, setEventForm] = useState({
    location: "",
    rainfall: 75,
    aqi: 180,
  });
  const [eventResult, setEventResult] = useState(null);

  const [payoutForm, setPayoutForm] = useState({
    worker_id: "",
    event_id: "",
    amount: 123.45,
  });
  const [payoutResult, setPayoutResult] = useState(null);

  const AUTH_KEY = "gw_worker_auth_v1";
  const THEME_KEY = "gw_theme_v1";

  const [theme, setTheme] = useState(() => localStorage.getItem(THEME_KEY) || "neon");
  const [auth, setAuth] = useState(() => {
    try {
      const raw = localStorage.getItem(AUTH_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    document.body.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  function applyAuth(worker) {
    if (!worker) return;
    setWorkerId(worker.worker_id);
    setWorkerForm({
      name: worker.name || "",
      location: worker.location || "",
      income: worker.income || 0,
    });
    setRiskForm((p) => ({ ...p, worker_id: worker.worker_id }));
    setPolicyForm((p) => ({ ...p, worker_id: worker.worker_id }));
    setPayoutForm((p) => ({ ...p, worker_id: worker.worker_id }));
    setEventForm((p) => ({ ...p, location: worker.location || p.location }));
  }

  useEffect(() => {
    if (auth) applyAuth(auth);
  }, []); // run once on mount

  useEffect(() => {
    try {
      if (auth) localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
      else localStorage.removeItem(AUTH_KEY);
    } catch {
      // ignore localStorage failures
    }
  }, [auth]);

  const [authMode, setAuthMode] = useState("register");
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });

  const riskPct = useMemo(() => {
    const v = Number(riskResult?.risk_score ?? 0);
    return Math.max(0, Math.min(100, Math.round(v * 100)));
  }, [riskResult]);

  const fraudKind = useMemo(() => {
    if (!riskResult) return null;
    if (riskResult.fraud_flag) return "bad";
    if (riskPct >= 70) return "warn";
    return "good";
  }, [riskResult, riskPct]);

  const donutStyle = useMemo(() => {
    const accent1 = "rgba(36,214,255,.95)";
    const accent2 = "rgba(124,92,255,.95)";
    // Fill risk percentage, keep rest in a dim ring.
    return {
      background: `conic-gradient(from 180deg, ${accent1} 0% ${riskPct}%, rgba(255,255,255,.10) ${riskPct}% 100%)`,
    };
  }, [riskPct]);

  const expectedPremium = useMemo(() => {
    if (!riskResult || !policyResult) return null;
    const base = Number(policyForm.base_price);
    const exp = Math.round(base * (1 + Number(riskResult.risk_score)) * 100) / 100;
    return exp;
  }, [riskResult, policyResult, policyForm.base_price]);

  function calcEventPayoutAmount(rainfall, aqi) {
    return Math.max((Number(rainfall) * 1.2) + (Number(aqi) * 0.2), 0);
  }

  function syncWorkerId(newId, locationOverride) {
    setWorkerId(newId);
    setRiskForm((p) => ({ ...p, worker_id: newId }));
    setPolicyForm((p) => ({ ...p, worker_id: newId }));
    setPayoutForm((p) => ({ ...p, worker_id: newId }));
    // Keep event location aligned with the selected worker zone.
    setEventForm((p) => ({ ...p, location: locationOverride || p.location || workerForm.location }));
  }

  async function handleRegister() {
    setError(null);
    setApiStatus("Working…");
    try {
      const data = await apiPost("/api/v1/workers/register", workerForm);
      const newAuth = {
        worker_id: data.worker_id,
        name: workerForm.name,
        location: data.location,
        income: workerForm.income,
        active: data.active,
      };
      setAuth(newAuth);
      syncWorkerId(newAuth.worker_id, newAuth.location);
      setApiStatus("Registered & logged in.");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function handleLogin() {
    setError(null);
    setApiStatus("Checking worker…");
    try {
      const data = await apiPost("/api/v1/workers/login", loginForm);
      const newAuth = {
        worker_id: data.worker_id,
        name: data.name,
        location: data.location,
        income: data.income,
        active: data.active,
      };
      setAuth(newAuth);
      syncWorkerId(newAuth.worker_id, newAuth.location);
      setApiStatus("Login successful.");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function handleCalculateRisk() {
    setError(null);
    setApiStatus("Calculating ML risk…");
    try {
      const data = await apiPost("/api/v1/risk/calculate", riskForm);
      setRiskResult(data);
      setApiStatus("Risk profile updated.");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function handlePurchasePolicy() {
    setError(null);
    setApiStatus("Purchasing weekly policy…");
    try {
      const data = await apiPost("/api/v1/policy/purchase", policyForm);
      setPolicyResult(data);
      setApiStatus("Policy activated.");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function handleTriggerEvent() {
    setError(null);
    setApiStatus("Triggering disruption event…");
    try {
      // event endpoint infers type from rainfall/aqi.
      const data = await apiPost("/api/v1/event/trigger", eventForm);
      setEventResult(data);
      const amt = calcEventPayoutAmount(eventForm.rainfall, eventForm.aqi);
      setPayoutForm((p) => ({ ...p, event_id: data.event_id, amount: amt }));
      setApiStatus("Event stored and payouts evaluated.");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function handleProcessPayout() {
    setError(null);
    setApiStatus("Processing payout (idempotent)…");
    try {
      const data = await apiPost("/api/v1/payout/process", payoutForm);
      setPayoutResult(data);
      setApiStatus(data.status === "already_processed" ? "Duplicate prevented." : "Payout processed.");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function handleFullSimulation() {
    setError(null);
    setApiStatus("Running full simulation…");
    try {
      const riskData = await apiPost("/api/v1/risk/calculate", riskForm);
      setRiskResult(riskData);

      const policyData = await apiPost("/api/v1/policy/purchase", policyForm);
      setPolicyResult(policyData);

      const eventData = await apiPost("/api/v1/event/trigger", eventForm);
      setEventResult(eventData);

      const amt = calcEventPayoutAmount(eventForm.rainfall, eventForm.aqi);
      setPayoutForm((p) => ({ ...p, event_id: eventData.event_id, amount: amt }));

      const payoutData = await apiPost("/api/v1/payout/process", {
        worker_id: auth.worker_id,
        event_id: eventData.event_id,
        amount: amt,
      });
      setPayoutResult(payoutData);

      setApiStatus("Simulation completed.");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  const step1Done = !!auth;
  const step2Done = !!riskResult;
  const step3Done = !!policyResult;
  const step4Done = !!eventResult;
  const step5Done = !!payoutResult;

  function handleLogout() {
    setAuth(null);
    setAuthMode("register");
    setWorkerId("");
    setRiskResult(null);
    setPolicyResult(null);
    setEventResult(null);
    setPayoutResult(null);
    setPayoutForm((p) => ({ ...p, event_id: "", amount: 123.45 }));
    setApiStatus(null);
    setError(null);
  }

  return (
    <div className="wrap">
      <div className="topbar">
        <div className="brand">
          <h1>Guidewire Premium Protection</h1>
          <p>ML risk → premium → event triggers → idempotent payouts</p>
        </div>
        <div className="row" style={{ justifyContent: "flex-end", gap: 10 }}>
          <div className="pill">API: http://127.0.0.1:8000</div>
          <button
            className="btn btnSecondary"
            onClick={() => setTheme((t) => (t === "neon" ? "midnight" : "neon"))}
            style={{ padding: "10px 12px" }}
          >
            Theme: {theme === "neon" ? "Neon" : "Midnight"}
          </button>
        </div>
      </div>

      {error ? <StatusBox kind="bad">{error}</StatusBox> : null}
      {apiStatus ? <div className="hint" style={{ marginBottom: 12 }}>{apiStatus}</div> : null}

      <div className="grid">
        {/* Left: Steps */}
        <div className="card">
          <div className="cardHeader">
            <h2>Workflow</h2>
            <div className="stepRow">
              <div className={`step ${step1Done ? "stepDone" : ""}`}>
                <strong>1</strong> Worker
              </div>
              <div className={`step ${step2Done ? "stepDone" : ""}`}>
                <strong>2</strong> ML Risk
              </div>
              <div className={`step ${step3Done ? "stepDone" : ""}`}>
                <strong>3</strong> Policy
              </div>
              <div className={`step ${step4Done ? "stepDone" : ""}`}>
                <strong>4</strong> Event
              </div>
              <div className={`step ${step5Done ? "stepDone" : ""}`}>
                <strong>5</strong> Payout
              </div>
            </div>
          </div>

          <div className="sectionTitle">1. Login / Register</div>
          {!auth ? (
            <>
              <div className="row" style={{ marginTop: 6 }}>
                <button
                  className={authMode === "register" ? "btn" : "btn btnSecondary"}
                  onClick={() => setAuthMode("register")}
                  style={{ padding: "10px 12px" }}
                >
                  Register
                </button>
                <button
                  className={authMode === "login" ? "btn" : "btn btnSecondary"}
                  onClick={() => setAuthMode("login")}
                  style={{ padding: "10px 12px" }}
                >
                  Login
                </button>
              </div>

              {authMode === "register" ? (
                <div className="formGrid" style={{ marginTop: 10 }}>
                  <div className="field">
                    <label>Name</label>
                    <input
                      value={workerForm.name}
                      onChange={(e) => setWorkerForm((p) => ({ ...p, name: e.target.value }))}
                      placeholder="e.g., Asha"
                    />
                  </div>
                  <div className="field">
                    <label>Email</label>
                    <input
                      type="email"
                      value={workerForm.email}
                      onChange={(e) => setWorkerForm((p) => ({ ...p, email: e.target.value }))}
                      placeholder="e.g., asha@example.com"
                    />
                  </div>
                  <div className="field">
                    <label>Password</label>
                    <input
                      type="password"
                      value={workerForm.password}
                      onChange={(e) => setWorkerForm((p) => ({ ...p, password: e.target.value }))}
                      placeholder="Min 6 chars"
                    />
                  </div>
                  <div className="field">
                    <label>Location (zone)</label>
                    <input
                      value={workerForm.location}
                      onChange={(e) => setWorkerForm((p) => ({ ...p, location: e.target.value }))}
                      placeholder="e.g., blr-east"
                    />
                  </div>
                  <div className="field">
                    <label>Daily income</label>
                    <input
                      type="number"
                      value={workerForm.income}
                      onChange={(e) => setWorkerForm((p) => ({ ...p, income: Number(e.target.value) }))}
                    />
                  </div>
                </div>
              ) : (
                <div className="formGrid" style={{ marginTop: 10 }}>
                  <div className="field">
                    <label>Email</label>
                    <input
                      type="email"
                      value={loginForm.email}
                      onChange={(e) => setLoginForm((p) => ({ ...p, email: e.target.value }))}
                      placeholder="Worker email"
                    />
                  </div>
                  <div className="field">
                    <label>Password</label>
                    <input
                      type="password"
                      value={loginForm.password}
                      onChange={(e) => setLoginForm((p) => ({ ...p, password: e.target.value }))}
                      placeholder="Password"
                    />
                  </div>
                </div>
              )}

              <div className="row" style={{ marginTop: 10 }}>
                <button
                  className="btn"
                  onClick={authMode === "register" ? handleRegister : handleLogin}
                  disabled={authMode === "login" && (!loginForm.email || !loginForm.password)}
                >
                  {authMode === "register" ? "Register & Login" : "Login"}
                </button>
                {/* Keep screen clean: no extra hint text. */}
              </div>
            </>
          ) : (
            <>
              <div className="alert good" style={{ marginTop: 10, marginBottom: 10 }}>
                <strong>Logged in</strong>
                <div className="hint" style={{ marginTop: 6 }}>
                  {auth.name} • {auth.location}
                </div>
                <div style={{ marginTop: 10 }}>
                  <button className="btn btnSecondary" onClick={handleLogout} style={{ padding: "10px 12px" }}>
                    Logout
                  </button>
                </div>
              </div>
              <div className="alert">
                <div className="hint mono">worker_id</div>
                <div style={{ wordBreak: "break-word", fontWeight: 850, marginTop: 4 }}>
                  {auth.worker_id}
                </div>
              </div>
            </>
          )}

          <div hidden={!auth}>
            <div className="divider" />

          <div className="sectionTitle">2. ML Risk Profiling</div>
          <div className="formGrid">
            <div className="field">
              <label>rainfall (mm)</label>
              <input
                type="number"
                value={riskForm.rainfall}
                onChange={(e) => setRiskForm((p) => ({ ...p, rainfall: Number(e.target.value) }))}
              />
            </div>
            <div className="field">
              <label>AQI</label>
              <input type="number" value={riskForm.aqi} onChange={(e) => setRiskForm((p) => ({ ...p, aqi: Number(e.target.value) }))} />
            </div>
            <div className="field">
              <label>temperature (°C)</label>
              <input
                type="number"
                value={riskForm.temperature}
                onChange={(e) => setRiskForm((p) => ({ ...p, temperature: Number(e.target.value) }))}
              />
            </div>
            <div className="field">
              <label>peak hours</label>
              <select value={riskForm.peak ? "yes" : "no"} onChange={(e) => setRiskForm((p) => ({ ...p, peak: e.target.value === "yes" }))}>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
            <div className="field">
              <label>location_risk (0..1)</label>
              <input
                type="number"
                step="0.1"
                value={riskForm.location_risk}
                onChange={(e) => setRiskForm((p) => ({ ...p, location_risk: Number(e.target.value) }))}
              />
            </div>
            <div className="field">
              <label>hours affected</label>
              <input
                type="number"
                value={riskForm.hours}
                onChange={(e) => setRiskForm((p) => ({ ...p, hours: Number(e.target.value) }))}
              />
            </div>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn" onClick={handleCalculateRisk} disabled={!auth}>Calculate Risk</button>
          </div>

          <div className="divider" />

          <div className="sectionTitle">3. Weekly Policy Purchase</div>
          <div className="formGrid">
            <div className="field">
              <label>base_price (₹)</label>
              <input type="number" value={policyForm.base_price} onChange={(e) => setPolicyForm((p) => ({ ...p, base_price: Number(e.target.value) }))} />
            </div>
            <div className="field">
              <label>coverage days</label>
              <input type="number" value={policyForm.days} onChange={(e) => setPolicyForm((p) => ({ ...p, days: Number(e.target.value) }))} />
            </div>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn btnSecondary" onClick={handlePurchasePolicy} disabled={!riskResult || !auth}>Purchase Policy</button>
          </div>

          <div className="divider" />

          <div className="sectionTitle">4. Trigger Event Engine</div>
          <div className="formGrid">
            <div className="field">
              <label>Event location (zone)</label>
              <input
                value={eventForm.location}
                disabled={!!auth}
                onChange={(e) => setEventForm((p) => ({ ...p, location: e.target.value }))}
                placeholder="same as worker location"
              />
            </div>
            <div className="field">
              <label>rainfall (mm)</label>
              <input type="number" value={eventForm.rainfall} onChange={(e) => setEventForm((p) => ({ ...p, rainfall: Number(e.target.value) }))} />
            </div>
            <div className="field">
              <label>AQI</label>
              <input type="number" value={eventForm.aqi} onChange={(e) => setEventForm((p) => ({ ...p, aqi: Number(e.target.value) }))} />
            </div>
            <div className="field">
              <label>event_id</label>
              <input value={eventResult?.event_id || ""} readOnly placeholder="after trigger" />
            </div>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn" onClick={handleTriggerEvent} disabled={!policyResult || !auth}>Trigger Event</button>
          </div>

          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn btnSecondary" onClick={handleFullSimulation} disabled={!auth}>
              Run Full Simulation
            </button>
          </div>

          <div className="divider" />

          <div className="sectionTitle">5. Payout (Idempotent)</div>
          <div className="formGrid">
            <div className="field">
              <label>amount (₹)</label>
              <input type="number" value={payoutForm.amount} onChange={(e) => setPayoutForm((p) => ({ ...p, amount: Number(e.target.value) }))} />
            </div>
            <div className="field">
              <label>payout status</label>
              <input value={payoutResult?.status || ""} readOnly placeholder="after process" />
            </div>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn" onClick={handleProcessPayout} disabled={!eventResult || !auth}>Process Payout</button>
          </div>
            </div>
        </div>

        {/* Right: Premium visuals */}
        <div className="card">
          <div className="cardHeader">
            <h2>Premium Look & Feel</h2>
            {/* Clean header: no extra text. */}
          </div>

          <div className="premiumHero card" style={{ padding: 14, marginBottom: 12 }}>
            <div className="heroRow">
              <div className="donutWrap" style={donutStyle}>
                <div className="donut">
                  <div className="pct">{riskPct}%</div>
                  <div className="lab">risk</div>
                </div>
              </div>
              <div>
                <div className="bigNum">
                  <Money value={policyResult?.premium ?? riskResult?.premium_quote} />
                  <span className="sub">/ week</span>
                </div>
                {/* Premium sync confirmed visually below. */}
                {expectedPremium !== null && policyResult && riskResult ? (
                  <div
                    className={
                      Math.abs(expectedPremium - Number(policyResult.premium)) < 0.01
                        ? "alert good"
                        : "alert warn"
                    }
                    style={{ marginTop: 10 }}
                  >
                    Premium sync:{" "}
                    {Math.abs(expectedPremium - Number(policyResult.premium)) < 0.01 ? "Matched" : "Mismatch"} (expected ₹
                    {Number(expectedPremium).toFixed(2)} / got ₹
                    {Number(policyResult.premium).toFixed(2)})
                  </div>
                ) : null}
              </div>
            </div>

            <div className="kpiGrid">
              <div className="kpi">
                <div className="label">Risk score</div>
                <div className="value mono">{riskResult ? riskResult.risk_score.toFixed(3) : "—"}</div>
              </div>
              <div className="kpi">
                <div className="label">Est. loss</div>
                <div className="value mono">
                  {riskResult ? (
                    <>₹{Number(riskResult.estimated_loss).toFixed(2)}</>
                  ) : (
                    "—"
                  )}
                </div>
              </div>
            </div>

            {riskResult ? (
              <div style={{ marginTop: 12 }}>
                <StatusBox kind={fraudKind}>
                  <strong>{riskResult.fraud_flag ? "Fraud heuristic: HIGH" : "Fraud heuristic: OK"}</strong>
                  <div className="hint" style={{ marginTop: 6 }}>
                    Real app would plug in advanced anti-spoof + anomaly checks.
                  </div>
                </StatusBox>
              </div>
            ) : null}
          </div>

          <div className="sectionTitle">Live IDs</div>
          <div className="alert" style={{ marginBottom: 10 }}>
            <div className="hint mono">worker_id</div>
            <div style={{ wordBreak: "break-word", fontWeight: 850, marginTop: 4 }}>
              {workerId || "—"}
            </div>
          </div>
          <div className="alert" style={{ marginBottom: 10 }}>
            <div className="hint mono">event_id</div>
            <div style={{ wordBreak: "break-word", fontWeight: 850, marginTop: 4 }}>
              {eventResult?.event_id || "—"}
            </div>
          </div>
          <div className="alert">
            <div className="hint mono">payout_id</div>
            <div style={{ wordBreak: "break-word", fontWeight: 850, marginTop: 4 }}>
              {payoutResult?.payout_id || "—"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

