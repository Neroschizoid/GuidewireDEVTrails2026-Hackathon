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
  const [registerForm, setRegisterForm] = useState({ name: "", location: "", income: 1000 });
  const [loginId, setLoginId] = useState("");

  const [apiStatus, setApiStatus] = useState(null);
  const [error, setError] = useState(null);

  const [online, setOnline] = useState(true);
  const [onlineSince, setOnlineSince] = useState(() => Date.now());
  const timerRef = useRef(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    timerRef.current = setInterval(() => setTick((x) => x + 1), 1000);
    return () => clearInterval(timerRef.current);
  }, []);
  useEffect(() => {
    if (online) setOnlineSince(Date.now());
  }, [online]);

  const [mlForm, setMlForm] = useState({
    rainfall: 80,
    aqi: 250,
    temperature: 30,
    peak: true,
    location_risk: 0.5,
    hours: 2,
    base_price: 20,
  });
  const [policyForm, setPolicyForm] = useState({ base_price: 20, days: 7 });
  const [triggerForm, setTriggerForm] = useState({ rainfall: 75, aqi: 180 });

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

  const riskPct = useMemo(() => {
    const v = Number(riskResult?.risk_score ?? 0);
    return clamp(Math.round(v * 100), 0, 100);
  }, [riskResult]);

  const tier = useMemo(() => {
    if (riskPct >= 75) return { key: "elite", name: "Elite Armor", base: 60, limit: 450, popular: false };
    if (riskPct >= 45) return { key: "pro", name: "Pro Armor", base: 40, limit: 300, popular: true };
    return { key: "basic", name: "Basic Shield", base: 20, limit: 150, popular: false };
  }, [riskPct]);

  useEffect(() => {
    setMlForm((p) => ({ ...p, base_price: tier.base }));
    setPolicyForm((p) => ({ ...p, base_price: tier.base }));
  }, [tier.base]);

  const totalSecured = payoutResult ? Number(payoutResult.amount) : 0;
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
      };
      setAuth(worker);
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
      const data = await apiGet(`/api/v1/workers/${loginId}`);
      setAuth({
        worker_id: data.worker_id,
        name: data.name,
        location: data.location,
        income: data.income,
        active: data.active,
      });
      resetSession();
      setApiStatus(null);
      setTab("dashboard");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function runML() {
    if (!auth) return;
    setError(null);
    setApiStatus("Running ML risk…");
    try {
      const payload = {
        worker_id: auth.worker_id,
        ...mlForm,
        location_risk: mlForm.location_risk,
      };
      const data = await apiPost("/api/v1/risk/calculate", payload);
      setRiskResult(data);
      setApiStatus(null);
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function buyPolicy() {
    if (!auth) return;
    setError(null);
    setApiStatus("Purchasing policy…");
    try {
      const payload = { worker_id: auth.worker_id, base_price: policyForm.base_price, days: policyForm.days };
      const data = await apiPost("/api/v1/policy/purchase", payload);
      setPolicyResult(data);
      setApiStatus(null);
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  function predictedPayout() {
    return Math.max(triggerForm.rainfall * 1.2 + triggerForm.aqi * 0.2, 0);
  }

  async function activateTrigger() {
    if (!auth) return;
    setError(null);
    setApiStatus("Activating parametric trigger…");
    try {
      const eventPayload = {
        location: auth.location,
        rainfall: triggerForm.rainfall,
        aqi: triggerForm.aqi,
      };
      const ev = await apiPost("/api/v1/event/trigger", eventPayload);
      setEventResult(ev);
      const amt = predictedPayout();
      const po = await apiPost("/api/v1/payout/process", {
        worker_id: auth.worker_id,
        event_id: ev.event_id,
        amount: amt,
      });
      setPayoutResult(po);
      setApiStatus(null);
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
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
                <button className="gwPrimaryBtn" onClick={handleRegister} disabled={!registerForm.name || !registerForm.location}>
                  Register & Activate
                </button>
              </>
            ) : (
              <>
                <label className="gwLabel" style={{ marginTop: 12 }}>
                  Worker ID
                  <input className="gwInput" value={loginId} onChange={(e) => setLoginId(e.target.value)} placeholder="Paste worker_id" />
                </label>
                <button className="gwPrimaryBtn" onClick={handleLogin} disabled={!loginId}>
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

                <div className="gwCard gwGlow" style={{ marginTop: 16 }}>
                  <div className="gwCardHead">
                    <div>
                      <div className="gwCardTitle">Upgrade Path</div>
                      <div className="gwMuted">Run ML and buy policy for your tier.</div>
                    </div>
                    <div className="gwTierPill">Current Tier: {tier.name}</div>
                  </div>
                  <div className="gwFormGrid">
                    <label className="gwLabel">
                      rainfall (mm)
                      <input className="gwInput" type="number" value={mlForm.rainfall} onChange={(e) => setMlForm((p) => ({ ...p, rainfall: Number(e.target.value) }))} />
                    </label>
                    <label className="gwLabel">
                      AQI
                      <input className="gwInput" type="number" value={mlForm.aqi} onChange={(e) => setMlForm((p) => ({ ...p, aqi: Number(e.target.value) }))} />
                    </label>
                  </div>
                  <div className="gwRow" style={{ marginTop: 12 }}>
                    <button className="gwPrimaryBtn" onClick={runML}>
                      Run ML Model
                    </button>
                    <button className="gwSecondaryBtn" onClick={buyPolicy} disabled={!riskResult}>
                      Buy Policy
                    </button>
                  </div>
                  {riskResult ? (
                    <div className="gwInlineStats">
                      <div className="gwStat">
                        <div className="gwStatLabel">Risk</div>
                        <div className="gwStatValue">{riskResult.risk_score.toFixed(2)}</div>
                      </div>
                      <div className="gwStat">
                        <div className="gwStatLabel">Premium Quote</div>
                        <div className="gwStatValue">₹{Number(riskResult.premium_quote).toFixed(2)}</div>
                      </div>
                      <div className="gwStat">
                        <div className="gwStatLabel">Est. Loss</div>
                        <div className="gwStatValue">₹{Number(riskResult.estimated_loss).toFixed(0)}</div>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}

            {tab === "tracker" ? (
              <div className="gwPage">
                <div className="gwCard gwGlow">
                  <div className="gwCardTitle">Tracker</div>
                  <div className="gwTrackerHero">
                    <div className={online ? "gwRing gwRingGreen" : "gwRing gwRingRed"}>
                      <div className="gwRingInner">
                        <div className="gwRingText">{online ? "GO ONLINE" : "GO OFFLINE"}</div>
                      </div>
                    </div>
                    <div className="gwTrackerMeta">
                      <div className="gwMetaLine">
                        <div className="gwMetaLabel">TIME ONLINE</div>
                        <div className="gwMetaValue">{online ? onlineDuration : "00:00"}</div>
                      </div>
                      <div className="gwMetaLine">
                        <div className="gwMetaLabel">MONITORED RISK</div>
                        <div className="gwMetaValue">Rain</div>
                      </div>
                      <div className="gwMetaLine">
                        <div className="gwMetaLabel">PROTECTED LIMIT</div>
                        <div className="gwMetaValue">₹{tier.limit}</div>
                      </div>
                      <div className="gwRow" style={{ marginTop: 12 }}>
                        <button className={online ? "gwToggle gwToggleOn" : "gwToggle"} onClick={() => setOnline(true)}>
                          Online
                        </button>
                        <button className={!online ? "gwToggle gwToggleOn" : "gwToggle"} onClick={() => setOnline(false)}>
                          Offline
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="gwDivider" />

                  <div className="gwTriggerCard">
                    <div className="gwTriggerTop">
                      <div className="gwTriggerTitle">PARAMETRIC TRIGGER</div>
                      <div className="gwTriggerAmount">+ ₹{Math.round(predictedPayout())}</div>
                    </div>
                    <div className="gwTriggerSub">Heavy rain automatically detected in your zone.</div>
                    <div className="gwFormGrid" style={{ marginTop: 12 }}>
                      <label className="gwLabel">
                        rainfall (mm)
                        <input
                          className="gwInput"
                          type="number"
                          value={triggerForm.rainfall}
                          onChange={(e) => setTriggerForm((p) => ({ ...p, rainfall: Number(e.target.value) }))}
                        />
                      </label>
                      <label className="gwLabel">
                        AQI
                        <input
                          className="gwInput"
                          type="number"
                          value={triggerForm.aqi}
                          onChange={(e) => setTriggerForm((p) => ({ ...p, aqi: Number(e.target.value) }))}
                        />
                      </label>
                    </div>
                    <div className="gwRow" style={{ marginTop: 12 }}>
                      <button className="gwPrimaryBtn" onClick={activateTrigger} disabled={!policyResult}>
                        Activate Trigger
                      </button>
                      <button
                        className="gwSecondaryBtn"
                        onClick={activateTrigger}
                        disabled={!policyResult || !eventResult}
                        title="Idempotent payout check"
                      >
                        Trigger Again
                      </button>
                    </div>
                    {payoutResult ? (
                      <div className="gwPayoutBox">
                        <div className="gwPayoutTop">
                          <div className="gwPayoutLabel">SECURED PALYOUT</div>
                          <div className="gwPayoutValue">{payoutResult.status === "already_processed" ? "IDEMPOTENT OK" : "PAYOUT READY"}</div>
                        </div>
                        <div className="gwPayoutAmount">
                          Amount: <strong>₹{Number(payoutResult.amount).toFixed(2)}</strong>
                        </div>
                        <div className="gwMuted" style={{ marginTop: 6, fontSize: 12 }}>
                          payout_id: {payoutResult.payout_id}
                        </div>
                      </div>
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
                    {[
                      { key: "basic", name: "Basic Shield", base: 20, limit: 150, triggers: ["Rain", "Heatwave"], popular: false, accent: "rgba(36,214,255,.25)" },
                      { key: "pro", name: "Pro Armor", base: 40, limit: 300, triggers: ["Rain", "Heatwave", "Traffic Halt"], popular: true, accent: "rgba(124,92,255,.30)" },
                      { key: "elite", name: "Elite Armor", base: 60, limit: 450, triggers: ["Rain", "Heatwave", "Curfew"], popular: false, accent: "rgba(255,77,141,.22)" },
                    ].map((t) => (
                      <div
                        key={t.key}
                        className={tier.key === t.key ? "gwTierCard gwTierCardActive" : "gwTierCard"}
                        style={{ borderColor: tier.key === t.key ? "rgba(36,214,255,.40)" : "rgba(255,255,255,.10)" }}
                      >
                        {t.popular ? <div className="gwBadge">MOST POPULAR</div> : null}
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
                          className={tier.key === t.key ? "gwPrimaryBtn gwPrimaryBtnSmall" : "gwSecondaryBtn gwPrimaryBtnSmall"}
                          onClick={() => {
                            setMlForm((p) => ({ ...p, base_price: t.base }));
                            setPolicyForm((p) => ({ ...p, base_price: t.base }));
                            // Encourage correct tier usage: clear previous results when changing tier.
                            resetSession();
                          }}
                        >
                          {tier.key === t.key ? "Selected" : "Select Tier"}
                        </button>
                      </div>
                    ))}
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
                      onClick={() => {
                        setAuth(null);
                        setTab("dashboard");
                        resetSession();
                      }}
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

