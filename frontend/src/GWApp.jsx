import React, { useEffect, useMemo, useRef, useState } from "react";
import { apiGet, apiPost } from "./api";

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function Money({ v }) {
  const n = Number(v);
  if (Number.isNaN(n)) return <span>₹0</span>;
  return <span>₹{n.toFixed(0)}</span>;
}

function ProgressBar({ value, max }) {
  const pct = max > 0 ? clamp((value / max) * 100, 0, 100) : 0;
  return (
    <div style={{ marginTop: 10 }}>
      <div
        style={{
          height: 10,
          borderRadius: 999,
          background: "rgba(255,255,255,.08)",
          border: "1px solid rgba(255,255,255,.10)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: "linear-gradient(90deg, rgba(36,214,255,.95), rgba(124,92,255,.95))",
            boxShadow: "0 0 22px rgba(124,92,255,.35)",
          }}
        />
      </div>
      <div className="gwMuted" style={{ marginTop: 8, fontSize: 12 }}>
        {Math.round(pct)}% complete
      </div>
    </div>
  );
}

function Icon({ name }) {
  const common = { width: 22, height: 22, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" };
  switch (name) {
    case "dashboard":
      return (
        <svg {...common}>
          <path d="M4 13h7V4H4v9Z" />
          <path d="M13 20h7V11h-7v9Z" />
          <path d="M13 4h7v7h-7V4Z" />
          <path d="M4 20h7v-7H4v7Z" />
        </svg>
      );
    case "tracker":
      return (
        <svg {...common}>
          <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" />
        </svg>
      );
    case "store":
      return (
        <svg {...common}>
          <path d="M6 2 3 6v16h18V6l-3-4H6Z" />
          <path d="M3 6h18" />
          <path d="M9 10v6" />
          <path d="M15 10v6" />
        </svg>
      );
    case "account":
      return (
        <svg {...common}>
          <path d="M20 21a8 8 0 0 0-16 0" />
          <path d="M12 11a4 4 0 1 0-4-4 4 4 0 0 0 4 4Z" />
        </svg>
      );
    default:
      return null;
  }
}

export default function GWApp() {
  const AUTH_KEY = "gw_worker_auth_v1";
  const [auth, setAuth] = useState(() => {
    try {
      const raw = localStorage.getItem(AUTH_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  const [tab, setTab] = useState("dashboard"); // dashboard | tracker | store | account
  const [theme, setTheme] = useState(() => localStorage.getItem("gw_theme_v1") || "neon");

  const [authMode, setAuthMode] = useState("register");
  const [registerForm, setRegisterForm] = useState({ name: "", email: "", password: "", location: "", income: 1000 });
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });

  const [apiStatus, setApiStatus] = useState(null);
  const [error, setError] = useState(null);

  // Online/Offline session management
  const [online, setOnline] = useState(false);  // default OFFLINE on login
  const [sessionId, setSessionId] = useState(null);
  const [onlineSince, setOnlineSince] = useState(() => Date.now());
  const timerRef = useRef(null);
  const pollRef = useRef(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    timerRef.current = setInterval(() => setTick((x) => x + 1), 1000);
    return () => clearInterval(timerRef.current);
  }, []);
  useEffect(() => {
    if (online) setOnlineSince(Date.now());
  }, [online]);

  const [geoCoords, setGeoCoords] = useState({ lat: 12.9716, lon: 77.5946 });

  useEffect(() => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition((pos) => {
        setGeoCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude });
      });
    }
  }, []);

  // Trigger check state
  const [triggerResult, setTriggerResult] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);
  const [autoClaimStatus, setAutoClaimStatus] = useState("idle"); // idle | checking | triggered | none

  const [riskResult, setRiskResult] = useState(null);
  const [policyResult, setPolicyResult] = useState(null);
  const [eventResult, setEventResult] = useState(null);
  const [payoutResult, setPayoutResult] = useState(null);

  useEffect(() => {
    document.body.dataset.theme = theme;
    localStorage.setItem("gw_theme_v1", theme);
  }, [theme]);

  useEffect(() => {
    try {
      if (auth) localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
      else localStorage.removeItem(AUTH_KEY);
    } catch {
      // ignore
    }
  }, [auth]);

  // Catch session expiry from api.js (refresh token expired)
  useEffect(() => {
    function handleExpiry() {
      setAuth(null);
      setTab("dashboard");
      resetSession();
      setError("Your session expired. Please log in again.");
    }
    window.addEventListener("gw:session_expired", handleExpiry);
    return () => window.removeEventListener("gw:session_expired", handleExpiry);
  }, []);

  const riskPct = useMemo(() => {
    const v = Number(riskResult?.risk_score ?? 0);
    return clamp(Math.round(v * 100), 0, 100);
  }, [riskResult]);

  const shieldsList = useMemo(() => [
    { p_id: 0, key: "none", name: "No Shield", base: 0, limit: 0, triggers: [], popular: false, accent: "transparent", price: 0 },
    { p_id: 1, key: "basic", name: "Basic Shield", base: 20, limit: 150, triggers: ["Rain", "Heatwave"], popular: false, accent: "rgba(36,214,255,.25)", price: 49 },
    { p_id: 2, key: "pro", name: "Pro Armor", base: 40, limit: 300, triggers: ["Rain", "Heatwave", "Traffic Halt"], popular: true, accent: "rgba(124,92,255,.30)", price: 99 },
    { p_id: 3, key: "elite", name: "Elite Armor", base: 60, limit: 450, triggers: ["Rain", "Heatwave", "Curfew"], popular: false, accent: "rgba(255,77,141,.22)", price: 149 },
  ], []);

  const [selectedShopTier, setSelectedShopTier] = useState(1);

  const tier = useMemo(() => {
    return shieldsList.find(s => s.p_id === (auth?.shield || 0)) || shieldsList[0];
  }, [auth?.shield, shieldsList]);

  const [mlForm, setMlForm] = useState({
    temperature: 30,
    peak: true,
    location_risk: 0.5,
    hours: 2,
    base_price: 20,
  });
  const [policyForm, setPolicyForm] = useState({ base_price: 20, days: 7 });

  const totalSecured = auth?.weekly_earnings || 0;
  const weeklyGoal = 10000;

  const onlineDuration = useMemo(() => {
    const ms = Math.max(0, Date.now() - onlineSince);
    const s = Math.floor(ms / 1000);
    const mm = String(Math.floor(s / 60)).padStart(2, "0");
    const ss = String(s % 60).padStart(2, "0");
    return `${mm}:${ss}`;
  }, [onlineSince, online, tick]);

  function resetSession() {
    setRiskResult(null);
    setPolicyResult(null);
    setEventResult(null);
    setPayoutResult(null);
    setApiStatus(null);
    setError(null);
    setTriggerResult(null);
    setLastChecked(null);
    setAutoClaimStatus("idle");
  }

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  async function handleRegister() {
    setError(null);
    setApiStatus("Registering…");
    try {
      const data = await apiPost("/api/v1/workers/register", registerForm);
      const worker = {
        worker_id: data.worker_id,
        name: registerForm.name,
        location: data.location,
        income: registerForm.income,
        active: data.active,
        shield: data.shield,
        active_policy: data.active_policy,
        weekly_earnings: data.weekly_earnings,
        access_token: data.access_token || "",
        refresh_token: data.refresh_token || "",
      };
      setAuth(worker);
      // Always start OFFLINE on login/register
      setOnline(false);
      setSessionId(null);
      stopPolling();
      resetSession();
      setApiStatus(null);
      setTab("dashboard");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function handleLogin() {
    setError(null);
    setApiStatus("Logging in…");
    try {
      const data = await apiPost("/api/v1/workers/login", loginForm);
      setAuth({
        worker_id: data.worker_id,
        name: data.name,
        location: data.location,
        income: data.income,
        active: data.active,
        shield: data.shield,
        active_policy: data.active_policy,
        weekly_earnings: data.weekly_earnings,
        access_token: data.access_token || "",
        refresh_token: data.refresh_token || "",
      });
      // Always start OFFLINE on login
      setOnline(false);
      setSessionId(null);
      stopPolling();
      resetSession();
      setApiStatus(null);
      setTab("dashboard");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function payForShield() {
    if (!auth) return;
    setError(null);
    const shopTier = shieldsList.find(s => s.p_id === selectedShopTier);
    if (!shopTier) return;
    const currentTierObj = shieldsList.find(s => s.p_id === (auth.shield || 0)) || shieldsList[0];
    const upgradePrice = Math.max(0, shopTier.price - currentTierObj.price);
    setApiStatus(`Processing ₹${upgradePrice} payment...`);
    try {
      const payload = { 
        worker_id: auth.worker_id, 
        p_id: selectedShopTier,
        risk_score: triggerResult?.risk_score || riskResult?.risk_score || 0.0,
        premium: triggerResult?.risk_score ? shopTier.price * triggerResult.risk_score : shopTier.price,
        days: policyForm.days || 7
      };
      const data = await apiPost("/api/v1/payment/process", payload);
      if (data.status) {
         setAuth(prev => ({ ...prev, shield: selectedShopTier, active_policy: true }));
         setApiStatus("Shield Upgrade Successful! You can now go Online to start monitoring.");
         setMlForm((p) => ({ ...p, base_price: shopTier.base }));
         setPolicyForm((p) => ({ ...p, base_price: shopTier.base }));
      } else {
         setError("Payment failed.");
         setApiStatus(null);
      }
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function handleRunML() {
    if (!auth) return;
    setError(null);
    setApiStatus("Analyzing current risk profile...");
    try {
      const payload = {
        worker_id: auth.worker_id,
        lat: geoCoords.lat,
        lon: geoCoords.lon,
        temperature: mlForm.temperature,
        peak: mlForm.peak,
        location_risk: mlForm.location_risk,
        hours: mlForm.hours,
        base_price: mlForm.base_price,
      };
      const data = await apiPost("/api/v1/risk/calculate", payload);
      setRiskResult(data);
      setApiStatus(null);
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }


  // ─── Session Lifecycle ───────────────────────────────────────
  async function goOnline() {
    if (!auth) return;
    setError(null);
    setApiStatus("Starting tracking session…");
    try {
      const data = await apiPost("/api/v1/session/start", {
        lat: geoCoords.lat,
        lon: geoCoords.lon,
      });
      setSessionId(data.session_id);
      setOnline(true);
      setApiStatus(null);
      setAutoClaimStatus("checking");
      // Fire immediately, then every 2.5 minutes
      await runCheckTriggers(data.session_id, false);
      pollRef.current = setInterval(() => runCheckTriggers(data.session_id, false), 150_000);
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function goOffline() {
    if (!auth) return;
    stopPolling();
    setOnline(false);
    setAutoClaimStatus("idle");
    if (sessionId) {
      try {
        await apiPost("/api/v1/session/end", {});
      } catch { /* ignore — session will expire naturally */ }
      setSessionId(null);
    }
  }

  // ─── Core automation: call /triggers/check ───────────────────
  async function runCheckTriggers(sid, simulate = false) {
    if (!auth) return;
    const sId = sid || sessionId;
    if (!sId) return;
    setAutoClaimStatus("checking");
    try {
      const data = await apiPost("/api/v1/triggers/check", {
        session_id: sId,
        lat: geoCoords.lat,
        lon: geoCoords.lon,
        temperature: mlForm.temperature,
        peak: mlForm.peak,
        location_risk: mlForm.location_risk,
        hours: mlForm.hours,
        simulate,
      });
      setTriggerResult(data);
      setLastChecked(new Date());
      setAutoClaimStatus(data.triggered ? "triggered" : "none");
      if (data.triggered && data.payout > 0) {
        setAuth(prev => ({ ...prev, weekly_earnings: (prev.weekly_earnings || 0) + Number(data.payout) }));
      }
    } catch (e) {
      setAutoClaimStatus("none");
      // Don't surface polling errors as loud UI errors
    }
  }

  function goToStore() {
    const recTier = triggerResult
      ? (triggerResult.risk_score >= 0.75 ? 3 : triggerResult.risk_score >= 0.45 ? 2 : 1)
      : 1;
    setSelectedShopTier(recTier);
    setTab("store");
  }

  // Cleanup polling on unmount
  useEffect(() => () => stopPolling(), []);

  // Stop tracking & session when user logs out
  function handleLogout() {
    stopPolling();
    if (sessionId) {
      apiPost("/api/v1/session/end", {}).catch(() => {});
    }
    setSessionId(null);
    setOnline(false);
    setAuth(null);
    setTab("dashboard");
    resetSession();
  }

  const nameInitial = (auth?.name || "U").trim().slice(0, 1).toUpperCase();

  return (
    <div className="gwBg">
      <div className="gwPhone">
        <div className="gwTop">
          <div>
            <div className="gwAppTitle">Parametric Shield</div>
            <div className="gwSubTitle">ML risk → premium → event triggers → secure payout</div>
          </div>
          <div className="gwTopRight">
            <button
              className="gwChip"
              onClick={() => setTheme((t) => (t === "neon" ? "midnight" : "neon"))}
              title="Theme"
            >
              Theme
            </button>
          </div>
        </div>

        {error ? <div className="gwAlert gwAlertBad">{error}</div> : null}
        {apiStatus ? <div className="gwAlert gwAlertWarn">{apiStatus}</div> : null}

        {!auth ? (
          <div className="gwAuthCard">
            <div className="gwAuthHead">
              <div className="gwAuthTitle">Welcome</div>
              <div className="gwAuthTabs">
                <button
                  className={authMode === "register" ? "gwTabActive" : "gwTab"}
                  onClick={() => setAuthMode("register")}
                >
                  Register
                </button>
                <button className={authMode === "login" ? "gwTabActive" : "gwTab"} onClick={() => setAuthMode("login")}>
                  Login
                </button>
              </div>
            </div>

            {authMode === "register" ? (
              <>
                <div className="gwFormGrid">
                  <label className="gwLabel">
                    Name
                    <input className="gwInput" value={registerForm.name} onChange={(e) => setRegisterForm((p) => ({ ...p, name: e.target.value }))} />
                  </label>
                  <label className="gwLabel">
                    Email
                    <input className="gwInput" type="email" value={registerForm.email} onChange={(e) => setRegisterForm((p) => ({ ...p, email: e.target.value }))} />
                  </label>
                  <label className="gwLabel">
                    Password
                    <input className="gwInput" type="password" value={registerForm.password} onChange={(e) => setRegisterForm((p) => ({ ...p, password: e.target.value }))} />
                  </label>
                  <label className="gwLabel">
                    Location (zone)
                    <input className="gwInput" value={registerForm.location} onChange={(e) => setRegisterForm((p) => ({ ...p, location: e.target.value }))} />
                  </label>
                  <label className="gwLabel">
                    Daily income
                    <input
                      className="gwInput"
                      type="number"
                      value={registerForm.income}
                      onChange={(e) => setRegisterForm((p) => ({ ...p, income: Number(e.target.value) }))}
                    />
                  </label>
                </div>
                <button className="gwPrimaryBtn" onClick={handleRegister} disabled={!registerForm.name || !registerForm.location || !registerForm.email || !registerForm.password}>
                  Register & Activate
                </button>
              </>
            ) : (
              <>
                <label className="gwLabel" style={{ marginTop: 12 }}>
                  Email
                  <input className="gwInput" type="email" value={loginForm.email} onChange={(e) => setLoginForm((p) => ({ ...p, email: e.target.value }))} placeholder="user@example.com" />
                </label>
                <label className="gwLabel" style={{ marginTop: 8 }}>
                  Password
                  <input className="gwInput" type="password" value={loginForm.password} onChange={(e) => setLoginForm((p) => ({ ...p, password: e.target.value }))} placeholder="Password" />
                </label>
                <button className="gwPrimaryBtn" style={{ marginTop: 16 }} onClick={handleLogin} disabled={!loginForm.email || !loginForm.password}>
                  Login & Load
                </button>
              </>
            )}
          </div>
        ) : null}

        {auth ? (
          <>
            {tab === "dashboard" ? (
              <div className="gwPage">
                <div className="gwCard gwGlow">
                  <div className="gwCardHead">
                    <div>
                      <div className="gwCardTitle">Total Secured Earnings</div>
                      <div className="gwBigMoney">
                        <Money v={totalSecured} />
                      </div>
                      <div className="gwMuted">Weekly Goal: ₹{weeklyGoal.toLocaleString("en-IN")}</div>
                    </div>
                    <div className="gwShield">🛡️</div>
                  </div>
                  <ProgressBar value={totalSecured} max={weeklyGoal} />
                </div>

                <div className="gwRow2">
                  <div className="gwCard">
                    <div className="gwCardTitle">Market Pulse</div>
                    <div className="gwPulseGrid">
                      <div className="gwPulseBlock">
                        <div className="gwPulseLabel">Risk Score</div>
                        <div className="gwPulseValue">{riskPct}/100</div>
                        <div className="gwMuted">{riskPct >= 50 ? "High" : "Low"} (zone forecast)</div>
                      </div>
                      <div className="gwPulseBlock">
                        <div className="gwPulseLabel">Active Tier</div>
                        <div className="gwPulseValue">{tier.name.replace("Armor", "Armor")}</div>
                        <div className="gwMuted">Coverage active</div>
                      </div>
                    </div>
                  </div>

                  <div className="gwCard">
                    <div className="gwCardTitle">Live Activity</div>
                    <div className="gwList">
                      <div className="gwListItem">
                        <span className={online ? "dot dotGreen" : "dot dotRed"} />
                        Status: {online ? "Online & Tracking" : "Offline Mode"}
                      </div>
                      <div className="gwListItem">
                        <span className={riskPct >= 70 ? "dot dotAmber" : "dot dotBlue"} />
                        Demand: {riskPct >= 70 ? "Extremely High" : riskPct >= 45 ? "Elevated" : "Normal"}
                      </div>
                      <div className="gwListItem">
                        <span className="dot dotPurple" />
                        Online duration: {online ? onlineDuration : "—"}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="gwCard" style={{ marginTop: 16, background: "rgba(124,92,255,.05)", border: "1px solid rgba(124,92,255,.2)" }}>
                  <div className="gwCardHead">
                    <div>
                      <div className="gwCardTitle" style={{ color: "#7c5cff" }}>Shield Advisor</div>
                      <div className="gwSubTitle">ML-powered risk assessment & recommendation</div>
                    </div>
                    <div className="gwShield">🧪</div>
                  </div>
                  
                  {riskResult ? (
                    <div style={{ marginTop: 12 }}>
                      <div className="gwRecBox">
                        <div style={{ fontSize: 13, marginBottom: 8 }}>
                          Current Risk Score: <strong style={{ color: "#24d6ff" }}>{(riskResult.risk_score * 100).toFixed(1)}%</strong>
                        </div>
                        <div style={{ fontSize: 14 }}>
                          Recommendation: Our model suggests the <strong style={{ color: "#7c5cff" }}>{riskResult.recommended_tier_name}</strong> for optimal coverage.
                        </div>
                      </div>
                      <div className="gwRow" style={{ marginTop: 12 }}>
                        <button className="gwPrimaryBtn" style={{ marginTop: 0 }} onClick={() => {
                          setSelectedShopTier(riskResult.recommended_tier);
                          setTab("store");
                        }}>
                          Get Protected
                        </button>
                        <button className="gwSecondaryBtn" onClick={handleRunML}>
                          Re-scan Risk
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ marginTop: 12 }}>
                      <div className="gwMuted" style={{ fontSize: 13, marginBottom: 12 }}>
                        Analyze your current environment (weather, location, hours) to find the best protection tier.
                      </div>
                      <button className="gwPrimaryBtn" onClick={handleRunML} style={{ marginTop: 0, background: "linear-gradient(90deg, #7c5cff, #ff4d8d)" }}>
                        Run ML Risk Scan
                      </button>
                    </div>
                  )}
                </div>

                <div className="gwCard gwGlow" style={{ marginTop: 16 }}>
                  <div className="gwCardHead">
                    <div>
                      <div className="gwCardTitle">Protection Status</div>
                      <div className="gwMuted">{auth?.active_policy ? "Shield active — go to Tracker to start monitoring." : "Purchase a shield in the Store to enable automated protection."}</div>
                    </div>
                    <div className="gwTierPill">Tier: {tier.name}</div>
                  </div>
                  <div className="gwInlineStats" style={{ marginTop: 12 }}>
                    <div className="gwStat">
                      <div className="gwStatLabel">RISK SCORE</div>
                      <div className="gwStatValue">{triggerResult ? triggerResult.risk_score.toFixed(2) : riskResult ? riskResult.risk_score.toFixed(2) : "—"}</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel">RAINFALL</div>
                      <div className="gwStatValue">{triggerResult ? `${triggerResult.rain.toFixed(1)} mm` : "—"}</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel">AQI</div>
                      <div className="gwStatValue">{triggerResult ? triggerResult.aqi.toFixed(0) : "—"}</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel">TEMP / PEAK</div>
                      <div className="gwStatValue">
                        {triggerResult ? `${triggerResult.temperature.toFixed(1)}° ${triggerResult.peak_status ? "⚡" : "○"}` : 
                         riskResult ? `${riskResult.temperature.toFixed(1)}° ${riskResult.peak_status ? "⚡" : "○"}` : "—"}
                      </div>
                    </div>
                  </div>
                  {auth?.active_policy ? (
                    <button className="gwPrimaryBtn" style={{ marginTop: 12 }} onClick={() => setTab("tracker")}>
                      {online ? "View Live Monitoring" : "Go Online to Start Monitoring"}
                    </button>
                  ) : (
                    <button className="gwSecondaryBtn" style={{ marginTop: 12 }} onClick={() => setTab("store")}>
                      Visit Policy Store
                    </button>
                  )}
                </div>
              </div>
            ) : null}

            {tab === "tracker" ? (
              <div className="gwPage">

                {/* ─── Session Control Ring ─── */}
                <div className="gwCard gwGlow">
                  <div className="gwCardTitle">Tracker</div>
                  <div className="gwTrackerHero">
                    <div
                      className={online ? "gwRing gwRingGreen" : "gwRing gwRingRed"}
                      onClick={online ? goOffline : (auth?.active_policy ? goOnline : undefined)}
                      style={{ cursor: auth?.active_policy ? "pointer" : "not-allowed" }}
                    >
                      <div className="gwRingInner">
                        <div className="gwRingText">{online ? "ONLINE" : "OFFLINE"}</div>
                      </div>
                    </div>
                    <div className="gwTrackerMeta">
                      <div className="gwMetaLine">
                        <div className="gwMetaLabel">TIME ONLINE</div>
                        <div className="gwMetaValue">{online ? onlineDuration : "00:00"}</div>
                      </div>
                      <div className="gwMetaLine">
                        <div className="gwMetaLabel">NEXT CHECK</div>
                        <div className="gwMetaValue">{online ? "Auto / 2.5 min" : "Offline"}</div>
                      </div>
                      <div className="gwMetaLine">
                        <div className="gwMetaLabel">PROTECTED LIMIT</div>
                        <div className="gwMetaValue">₹{tier.limit}</div>
                      </div>
                      <div className="gwRow" style={{ marginTop: 12 }}>
                        <button
                          className={!online ? "gwPrimaryBtn" : "gwSecondaryBtn"}
                          onClick={online ? goOffline : goOnline}
                          disabled={!auth?.active_policy}
                          title={!auth?.active_policy ? "Purchase a shield in the Store first" : ""}
                        >
                          {online ? "Stop Monitoring" : "GO ONLINE"}
                        </button>
                      </div>
                      {!auth?.active_policy ? (
                        <div className="gwMuted" style={{ fontSize: 11, marginTop: 6 }}>Purchase a shield tier to enable monitoring.</div>
                      ) : null}
                    </div>
                  </div>
                </div>

                {/* ─── Risk Engine Monitor ─── */}
                <div className="gwCard" style={{ marginTop: 12 }}>
                  <div className="gwCardHead">
                    <div className="gwCardTitle">Risk Engine</div>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span style={{
                        fontSize: 11, padding: "2px 8px", borderRadius: 999,
                        background: autoClaimStatus === "triggered" ? "rgba(36,214,100,.25)" :
                                    autoClaimStatus === "checking" ? "rgba(255,190,30,.25)" :
                                    "rgba(255,255,255,.08)",
                        color: autoClaimStatus === "triggered" ? "#24d664" :
                               autoClaimStatus === "checking" ? "#ffbe1e" : "rgba(255,255,255,.5)"
                      }}>
                        {autoClaimStatus === "triggered" ? "✓ TRIGGERED" :
                         autoClaimStatus === "checking" ? "⟳ CHECKING" :
                         autoClaimStatus === "none" ? "● MONITORING" : "○ IDLE"}
                      </span>
                      <button className="gwSecondaryBtn" style={{ padding: "4px 10px", fontSize: 12 }}
                        onClick={() => runCheckTriggers(sessionId, false)}
                        disabled={!online}
                      >Refresh</button>
                    </div>
                  </div>
                  <div className="gwInlineStats" style={{ marginTop: 10 }}>
                    <div className="gwStat">
                      <div className="gwStatLabel">RAINFALL</div>
                      <div className="gwStatValue" style={{ color: (triggerResult?.rain || 0) > 50 ? "#ff6b6b" : undefined }}>
                        {triggerResult ? `${triggerResult.rain.toFixed(1)} mm` : "—"}
                      </div>
                      <div className="gwMuted" style={{ fontSize: 10 }}>Threshold: &gt;50mm</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel">AQI</div>
                      <div className="gwStatValue" style={{ color: (triggerResult?.aqi || 0) > 200 ? "#ff6b6b" : undefined }}>
                        {triggerResult ? triggerResult.aqi.toFixed(0) : "—"}
                      </div>
                      <div className="gwMuted" style={{ fontSize: 10 }}>Threshold: &gt;200</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel">RISK SCORE</div>
                      <div className="gwStatValue">
                        {triggerResult ? (triggerResult.risk_score * 100).toFixed(0) + "/100" : "—"}
                      </div>
                      <div className="gwMuted" style={{ fontSize: 10 }}>
                        {lastChecked ? `${lastChecked.toLocaleTimeString()}` : "Not checked yet"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* ─── Protection Status / Auto Claim ─── */}
                <div className="gwCard" style={{ marginTop: 12 }}>
                  <div className="gwCardHead">
                    <div className="gwCardTitle">Auto Protection</div>
                    <div style={{ fontSize: 12, color: online ? "#24d6ff" : "rgba(255,255,255,.4)" }}>
                      {online ? "● Active" : "○ Inactive"}
                    </div>
                  </div>
                  <div className="gwList">
                    <div className="gwListItem">
                      <span className={online ? "dot dotGreen" : "dot dotRed"} />
                      Monitoring: {online ? "Online & Tracking" : "Offline"}
                    </div>
                    <div className="gwListItem">
                      <span className={triggerResult?.triggered ? "dot dotAmber" : "dot dotBlue"} />
                      Last Event: {triggerResult?.triggered ? triggerResult.trigger_type?.toUpperCase() + " DETECTED" : "None"}
                    </div>
                    <div className="gwListItem">
                      <span className={autoClaimStatus === "triggered" ? "dot dotGreen" : "dot dotPurple"} />
                      Claim Status: {autoClaimStatus === "triggered" ? "Auto-created ✓" : autoClaimStatus === "checking" ? "Processing…" : "Standing by"}
                    </div>
                    {triggerResult?.triggered && triggerResult?.payout ? (
                      <div className="gwPayoutBox" style={{ marginTop: 8 }}>
                        <div className="gwPayoutTop">
                          <div className="gwPayoutLabel">AUTO CLAIM SECURED</div>
                          <div className="gwPayoutValue">PAYOUT READY</div>
                        </div>
                        <div className="gwPayoutAmount">
                          Amount: <strong>₹{Number(triggerResult.payout).toFixed(2)}</strong>
                        </div>
                        <div className="gwMuted" style={{ marginTop: 4, fontSize: 11 }}>
                          {triggerResult.message}
                        </div>
                      </div>
                    ) : null}
                  </div>
                  <div className="gwRow" style={{ marginTop: 12 }}>
                    <button
                      className="gwSecondaryBtn"
                      onClick={() => runCheckTriggers(sessionId, true)}
                      disabled={!online}
                      title="Inject simulated heavy rain for demo"
                    >
                      Simulate Event
                    </button>
                    {triggerResult && triggerResult.risk_score >= 0.45 && (auth?.shield || 0) < (triggerResult.risk_score >= 0.75 ? 3 : 2) ? (
                      <button className="gwSecondaryBtn" onClick={goToStore}>
                        Upgrade Shield
                      </button>
                    ) : null}
                  </div>
                </div>

              </div>
            ) : null}

            {tab === "store" ? (
              <div className="gwPage">
                <div className="gwCard gwGlow">
                  <div className="gwStoreTitle">Policy Store</div>
                  <div className="gwMuted">Upgrade your shield to maximize payouts.</div>

                  <div className="gwCurrentTier">
                    <div className="gwCheck">✓</div>
                    <div>
                      <div className="gwMuted">CURRENT TIER</div>
                      <div className="gwTierName">{tier.name}</div>
                    </div>
                  </div>

                  <div className="gwTierGrid">
                    {shieldsList.filter(t => t.p_id > 0).map((t) => (
                      <div
                        key={t.key}
                        className={selectedShopTier === t.p_id ? "gwTierCard gwTierCardActive" : "gwTierCard"}
                        style={{ borderColor: selectedShopTier === t.p_id ? "rgba(36,214,255,.40)" : "rgba(255,255,255,.10)" }}
                      >
                        {t.popular ? <div className="gwBadge">MOST POPULAR</div> : null}
                        {riskResult?.recommended_tier === t.p_id ? (
                          <div className="gwBadge" style={{ 
                            right: t.popular ? 140 : 12, 
                            background: "rgba(124,92,255,.15)", 
                            color: "#7c5cff", 
                            borderColor: "rgba(124,92,255,.3)" 
                          }}>
                            RECOMMENDED
                          </div>
                        ) : null}
                        <div className="gwTierCardHead">
                          <div>
                            <div className="gwTierCardName">{t.name}</div>
                            <div className="gwTierCardSub">Base {t.base} /wk</div>
                          </div>
                          <div className="gwTierLimit">₹{t.limit}</div>
                        </div>
                        <div className="gwTriggerChips">
                          {t.triggers.slice(0, 3).map((x) => (
                            <span key={x} className="gwTriggerChip">
                              {x}
                            </span>
                          ))}
                        </div>
                        <button
                          className={selectedShopTier === t.p_id ? "gwPrimaryBtn gwPrimaryBtnSmall" : "gwSecondaryBtn gwPrimaryBtnSmall"}
                          onClick={() => setSelectedShopTier(t.p_id)}
                          disabled={t.p_id < (auth?.shield || 0) || (t.p_id === (auth?.shield || 0) && auth?.active_policy)}
                          style={{ opacity: t.p_id < (auth?.shield || 0) || (t.p_id === (auth?.shield || 0) && auth?.active_policy) ? 0.5 : 1 }}
                        >
                          {t.p_id === (auth?.shield || 0) ? (auth?.active_policy ? "Active Tier" : "Expired - Renew") : t.p_id < (auth?.shield || 0) ? "Owned" : selectedShopTier === t.p_id ? "Selected" : "Select Tier"}
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="gwRow" style={{ marginTop: 16 }}>
                    <button className="gwPrimaryBtn" onClick={payForShield} disabled={(selectedShopTier < (auth?.shield || 0)) || (selectedShopTier === (auth?.shield || 0) && auth?.active_policy)}>
                      Pay ₹{Math.max(0, (shieldsList.find(s => s.p_id === selectedShopTier)?.price || 0) - (auth?.active_policy ? (shieldsList.find(s => s.p_id === (auth?.shield || 0))?.price || 0) : 0))} to {selectedShopTier === (auth?.shield || 0) ? "Renew" : "Upgrade"}
                    </button>
                  </div>

                  <div className="gwDivider" style={{ marginTop: 16 }} />

                  <div className="gwMuted" style={{ fontSize: 12 }}>
                    Tip: Run ML Model after selecting tier, then Buy Policy.
                  </div>
                </div>
              </div>
            ) : null}

            {tab === "account" ? (
              <div className="gwPage">
                <div className="gwCard gwGlow">
                  <div className="gwAccountHead">
                    <div className="gwAvatar">{nameInitial}</div>
                    <div>
                      <div className="gwMuted">Welcome back,</div>
                      <div className="gwAccountName">{auth.name}</div>
                    </div>
                    <div className="gwShieldBig">🛡️</div>
                  </div>

                  <div className="gwInlineStats" style={{ marginTop: 10 }}>
                    <div className="gwStat">
                      <div className="gwStatLabel">TOTAL SECURED</div>
                      <div className="gwStatValue">₹{Number(totalSecured).toFixed(0)}</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel">ACTIVE TIER</div>
                      <div className="gwStatValue">{tier.name}</div>
                    </div>
                  </div>

                  <div className="gwDivider" />

                  <div className="gwTwoCols">
                    <div className="gwCardInner">
                      <div className="gwMuted">Risk Score</div>
                      <div className="gwBigScore">{riskPct}/100</div>
                      <div className="gwMuted" style={{ marginTop: 6, fontSize: 12 }}>
                        Based on ML inference inputs.
                      </div>
                    </div>
                    <div className="gwCardInner">
                      <div className="gwMuted">Premium</div>
                      <div className="gwBigScore">
                        ₹{policyResult ? Number(policyResult.premium).toFixed(2) : riskResult ? Number(riskResult.premium_quote).toFixed(2) : "0.00"}
                      </div>
                      <div className="gwMuted" style={{ marginTop: 6, fontSize: 12 }}>
                        Sync with ML risk via base_price.
                      </div>
                    </div>
                  </div>

                  <div className="gwRow" style={{ marginTop: 14 }}>
                    <button
                      className="gwSecondaryBtn"
                      onClick={handleLogout}
                    >
                      Logout
                    </button>
                    <button className="gwPrimaryBtn" onClick={() => setTab("tracker")}>
                      Go to Tracker
                    </button>
                  </div>
                </div>
              </div>
            ) : null}
          </>
        ) : null}

        {auth ? (
          <div className="gwBottomNav">
            <button className={tab === "dashboard" ? "gwNavItem gwNavItemActive" : "gwNavItem"} onClick={() => setTab("dashboard")}>
              <Icon name="dashboard" />
              <span>Dashboard</span>
            </button>
            <button className={tab === "tracker" ? "gwNavItem gwNavItemActive" : "gwNavItem"} onClick={() => setTab("tracker")}>
              <Icon name="tracker" />
              <span>Tracker</span>
            </button>
            <button className={tab === "store" ? "gwNavItem gwNavItemActive" : "gwNavItem"} onClick={() => setTab("store")}>
              <Icon name="store" />
              <span>Store</span>
            </button>
            <button className={tab === "account" ? "gwNavItem gwNavItemActive" : "gwNavItem"} onClick={() => setTab("account")}>
              <Icon name="account" />
              <span>Account</span>
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

