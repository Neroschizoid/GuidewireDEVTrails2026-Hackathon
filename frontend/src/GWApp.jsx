import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { apiDelete, apiGet, apiPost } from "./api";
import AdminDashboard from "./AdminDashboard";
import { clearAuthSession, getStoredAuth, setAuthSession } from "./authStorage";
import { apiLogout } from "./api";

const QUOTES = [
  "Risk is the price of progress.",
  "True protection is invisible.",
  "Data is the shield of the modern era.",
  "Uncertainty is the only certainty there is.",
  "Preparation is the ultimate advantage.",
  "Resilience is built ahead of the storm.",
  "Parametric logic executes with zero-touch precision.",
  "To anticipate is to mitigate.",
  "Fortune favors the prepared.",
  "Empowering the gig economy through smart contracts.",
  "Security is not a product, but a process.",
  "Trust is forged in transparency.",
  "Bridging the gap between danger and safety.",
  "Proactive defense is the best strategy.",
  "Algorithmic precision equals financial peace.",
  "We don't predict the future, we insure it.",
  "Coverage as fluid as the changing climate.",
  "Harnessing ML for equitable protection.",
  "Invisible safety nets for visible progress.",
  "When conditions are met, action is guaranteed."
];

const ParticleSwarm = () => {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let width, height;
    let particles = [];
    const PARTICLE_COUNT = Math.min(window.innerWidth > 768 ? 400 : 150, 400);

    const mouse = { x: window.innerWidth / 2, y: window.innerHeight / 2, moved: false };
    const center = { x: window.innerWidth / 2, y: window.innerHeight / 2 };

    const resize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      if (!mouse.moved) {
        mouse.x = width / 2;
        mouse.y = height / 2;
      }
    };
    
    const onMouseMove = (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.moved = true;
    };

    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', onMouseMove);
    resize();

    class Particle {
      constructor() {
        this.angle = Math.random() * Math.PI * 2;
        this.radius = Math.random() * Math.min(width, height) * 0.5;
        this.baseRadius = this.radius;
        this.speed = (Math.random() - 0.5) * 0.003;
        this.size = Math.random() * 1.5 + 0.5;
        const colors = ['#58A6FF', '#3B82F6', '#F85149', '#D29922', '#1C2128'];
        this.color = colors[Math.floor(Math.random() * colors.length)];
      }
      update(cx, cy) {
        this.angle += this.speed;
        this.x = cx + Math.cos(this.angle) * this.radius;
        this.y = cy + Math.sin(this.angle) * this.radius;
        this.radius = this.baseRadius + Math.sin(Date.now() * 0.001 + this.angle) * 8;
      }
      draw(cx, cy) {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        const dist = Math.hypot(this.x - cx, this.y - cy);
        ctx.globalAlpha = Math.max(0.1, 1 - dist / (Math.max(width, height) * 0.5));
        ctx.fill();
        ctx.globalAlpha = 1;
      }
    }
    for (let i = 0; i < PARTICLE_COUNT; i++) particles.push(new Particle());

    let animationFrame;
    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Smoothly interpolate center towards mouse
      center.x += (mouse.x - center.x) * 0.05;
      center.y += (mouse.y - center.y) * 0.05;

      particles.forEach(p => {
        p.update(center.x, center.y);
        p.draw(center.x, center.y);
      });
      animationFrame = requestAnimationFrame(render);
    };
    render();

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', onMouseMove);
      cancelAnimationFrame(animationFrame);
    };
  }, []);
  return <canvas ref={canvasRef} style={{ position: 'fixed', top: 0, left: 0, zIndex: -1, background: 'transparent', pointerEvents: 'none' }} />;
};

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function loadExternalScript(src) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      resolve(true);
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => reject(new Error(`Unable to load ${src}`));
    document.body.appendChild(script);
  });
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

function AdminView() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(false);

  async function fetchClaims() {
    setLoading(true);
    try {
      const data = await apiGet("/api/v1/admin/flagged_claims");
      setClaims(data || []);
    } catch {
      setClaims([]);
    }
    setLoading(false);
  }

  useEffect(() => {
    fetchClaims();
  }, []);

  async function resolveClaim(id) {
    try {
      await apiPost(`/api/v1/admin/resolve_claim/${id}`, {});
      fetchClaims();
    } catch {}
  }

  return (
    <motion.div key="admin" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.2 }} className="gwPage">
      <div className="gwCard gwGlow">
        <div className="gwCardTitle" style={{ color: "#ff4d8d" }}>Security & Fraud Review</div>
        <div className="gwMuted">Flagged claims awaiting manual verification.</div>
        
        {loading ? (
          <div style={{ marginTop: 16 }}>Loading flagged claims...</div>
        ) : claims.length === 0 ? (
          <div style={{ marginTop: 16 }} className="gwMuted">All clears. No flagged claims found.</div>
        ) : (
          <div className="gwList" style={{ marginTop: 16 }}>
            {claims.map(c => (
              <div key={c.payout_id} className="gwListItem" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <strong>{c.worker_name}</strong>
                    <span className="gwBadge" style={{ background: "rgba(255,77,141,0.15)", color: "#ff4d8d" }}>FLAGGED</span>
                  </div>
                  <div className="gwMuted" style={{ fontSize: 12, marginTop: 4 }}>
                    Payout Amount: ₹{c.amount} | Fraud Score: {c.fraud_score}/100
                  </div>
                  <div style={{ fontSize: 11, color: "var(--danger)", marginTop: 4 }}>
                    Reason: {c.fraud_reason || "Unspecified"}
                  </div>
                </div>
                <button className="gwSecondaryBtn" style={{ padding: "4px 12px", fontSize: 11 }} onClick={() => resolveClaim(c.payout_id)}>Clear & Process</button>
              </div>
            ))}
          </div>
        )}
        <button className="gwPrimaryBtn" style={{ marginTop: 16 }} onClick={fetchClaims}>Refresh View</button>
      </div>
    </motion.div>
  );
}

function RollingNumber({ val }) {
  const [disp, setDisp] = useState(0);
  useEffect(() => {
    let start = disp;
    let end = Number(val) || 0;
    if (start === end) return;
    let duration = 1500;
    let startTime = null;
    const step = (now) => {
      if (!startTime) startTime = now;
      const progress = Math.min((now - startTime) / duration, 1);
      const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      setDisp(start + (end - start) * ease);
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [val]);
  return <span>₹{Number(disp).toFixed(0)}</span>;
}

function PaymentGatewayModal({ open, triggerData, onClose, onSettled }) {
  const onSettledRef = useRef(onSettled);

  useEffect(() => {
    onSettledRef.current = onSettled;
  }, [onSettled]);

  useEffect(() => {
    if (open && onSettledRef.current) {
      onSettledRef.current();
    }
  }, [open]);

  if (!open || !triggerData) return null;

  return (
    <div className="gwGlassModalOverlay">
      <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="gwGlassModal">
        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="gwPaymentSuccess gwPulseGlow">OK</motion.div>
        <h3 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>Payout Recorded</h3>
        <div className="gwMuted" style={{ marginTop: 8, fontSize: 14 }}>
          Claim ID: {triggerData.claim_id || "Unavailable"}
        </div>
        <div className="gwBigMoney" style={{ marginTop: 24, color: '#24d6ff' }}>+Rs {triggerData.payout}</div>
        <div className="gwMuted" style={{ marginTop: 16, fontSize: 12 }}>
          Trigger: {(triggerData.trigger_type || "unknown").toUpperCase()} | Risk {(triggerData.risk_score * 100).toFixed(0)}/100
        </div>
        <div className="gwMuted" style={{ marginTop: 8, fontSize: 12 }}>
          Transfer: {(triggerData.transfer_status || "queued").toUpperCase()} via {(triggerData.payout_gateway || "upi_simulator").toUpperCase()}
        </div>
        <div className="gwMuted" style={{ marginTop: 6, fontSize: 12 }}>
          Ref: {triggerData.payout_reference || "Pending"}{triggerData.beneficiary_masked ? ` • Beneficiary ${triggerData.beneficiary_masked}` : ""}
        </div>
        <div className="gwMuted" style={{ marginTop: 8, fontSize: 12 }}>
          {triggerData.message}
        </div>
        <button className="gwPrimaryBtn" style={{ marginTop: 24 }} onClick={onClose}>Close</button>
      </motion.div>
    </div>
  );
}

function ToastContainer({ toasts }) {
  return (
    <div className="gwToastContainer">
      <AnimatePresence>
        {toasts.map(t => (
          <motion.div key={t.id} initial={{ opacity: 0, x: 50 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 50 }} className="gwToast">
            <div className="gwToastIcon">✓</div>
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{t.title}</div>
              <div style={{ fontSize: 12, opacity: 0.8, marginTop: 4 }}>{t.message}</div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

export default function GWApp() {
  const [auth, setAuth] = useState(() => getStoredAuth());

  const [tab, setTab] = useState("dashboard"); // dashboard | tracker | store | admin | account
  const [theme, setTheme] = useState(() => localStorage.getItem("gw_theme_v1") || "light");

  const [accountTab, setAccountTab] = useState("active");
  const [payoutHistory, setPayoutHistory] = useState([]);

  const [gatewayOpen, setGatewayOpen] = useState(false);
  const [gatewayData, setGatewayData] = useState(null);
  const [toasts, setToasts] = useState([]);
  
  function addToast(title, message) {
    const id = Date.now();
    setToasts(prev => [...prev, { id, title, message }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }

  useEffect(() => {
    if (tab === "account" && accountTab === "recent") {
      apiGet("/api/v1/payout/history").then(d => setPayoutHistory(d || []));
    }
  }, [tab, accountTab]);

  useEffect(() => {
    apiGet("/api/v1/payment/gateways")
      .then((data) => {
        setGatewayCatalog(data || { payment_gateways: [], payout_gateways: [] });
      })
      .catch(() => {
        setGatewayCatalog({ payment_gateways: [], payout_gateways: [] });
      });
  }, []);

  useEffect(() => {
    if (auth?.bank_account_linked) {
      setBankStatus({
        linked: true,
        verified: true,
        account_holder: auth.bank_account_holder || "",
        bank_name: auth.bank_name || "",
        account_masked: auth.bank_account_masked || "",
      });
      setBankForm((prev) => ({
        ...prev,
        account_holder: auth.bank_account_holder || "",
        bank_name: auth.bank_name || "",
        preferred_payout_gateway: auth.preferred_payout_gateway || prev.preferred_payout_gateway,
      }));
    } else {
      setBankStatus(null);
      setBankForm((prev) => ({
        ...prev,
        account_holder: "",
        bank_name: "",
        account_number: "",
        ifsc: "",
        preferred_payout_gateway: prev.preferred_payout_gateway || "upi_simulator",
      }));
    }
  }, [auth?.bank_account_holder, auth?.bank_account_linked, auth?.bank_account_masked, auth?.bank_name, auth?.preferred_payout_gateway]);

  useEffect(() => {
    async function loadAccountSettings() {
      if (!auth?.worker_id || tab !== "account" || accountTab !== "active") return;
      setAccountSettingsLoading(true);
      try {
        const [workerData, bankData] = await Promise.all([
          apiGet(`/api/v1/workers/${auth.worker_id}`),
          apiGet("/api/v1/workers/bank-account"),
        ]);

        setAuth((prev) => ({
          ...prev,
          worker_id: workerData.worker_id,
          name: workerData.name,
          email: workerData.email,
          location: workerData.location,
          income: workerData.income,
          active: workerData.active,
          shield: workerData.shield,
          weekly_earnings: workerData.weekly_earnings,
          active_policy: workerData.active_policy,
          policy_start_date: workerData.policy_start_date || null,
          policy_end_date: workerData.policy_end_date || null,
          trust_score: workerData.trust_score || 100,
          two_factor_enabled: workerData.two_factor_enabled ?? false,
          bank_account_linked: workerData.bank_account_linked ?? false,
          bank_account_masked: workerData.bank_account_masked || null,
          bank_name: workerData.bank_name || null,
          bank_account_holder: workerData.bank_account_holder || null,
          preferred_payout_gateway: bankData.preferred_payout_gateway || null,
        }));

        setBankStatus(bankData);
        setBankForm((prev) => ({
          ...prev,
          account_holder: bankData.account_holder || "",
          bank_name: bankData.bank_name || "",
          preferred_payout_gateway: bankData.preferred_payout_gateway || prev.preferred_payout_gateway || "upi_simulator",
        }));
      } catch (e) {
        setError(String(e?.message || e));
      } finally {
        setAccountSettingsLoading(false);
      }
    }

    loadAccountSettings();
  }, [accountTab, auth?.worker_id, tab]);


  const [authMode, setAuthMode] = useState("register");
  const [registerForm, setRegisterForm] = useState({ name: "", email: "", password: "", location: "", income: 1000 });
  const [loginForm, setLoginForm] = useState({ email: "", password: "", otp_code: "" });
  const [twoFactorSetup, setTwoFactorSetup] = useState(null);
  const [twoFactorCode, setTwoFactorCode] = useState("");
  const [bankForm, setBankForm] = useState({ account_holder: "", bank_name: "", account_number: "", ifsc: "", preferred_payout_gateway: "upi_simulator" });
  const [bankStatus, setBankStatus] = useState(null);
  const [accountSettingsLoading, setAccountSettingsLoading] = useState(false);
  const [gatewayCatalog, setGatewayCatalog] = useState({ payment_gateways: [], payout_gateways: [] });
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleteInFlight, setDeleteInFlight] = useState(false);

  const [quoteIndex, setQuoteIndex] = useState(0);

  // Rotate quotes every 60 seconds
  useEffect(() => {
    const quoteInterval = setInterval(() => {
      setQuoteIndex((i) => (i + 1) % QUOTES.length);
    }, 45000);
    return () => clearInterval(quoteInterval);
  }, []);

  // Keyboard navigation shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "TEXTAREA") return;
      if (e.key === "1") setTab("dashboard");
      else if (e.key === "2") setTab("tracker");
      else if (e.key === "3") setTab("store");
      else if (e.key === "4") setTab("admin");
      else if (e.key === "5") setTab("account");
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

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

  const activeWeatherResult = triggerResult || riskResult;
  const weatherUnavailable = Boolean(activeWeatherResult?.weather_unavailable);
  const currentRainfall = Number(activeWeatherResult?.rain ?? 0);
  const currentAqi = Number(activeWeatherResult?.aqi ?? 0);
  const currentRiskScore = activeWeatherResult?.risk_score;
  const currentEstimatedLoss = Number(activeWeatherResult?.estimated_loss ?? 0);
  const currentTemperature = Number(activeWeatherResult?.temperature ?? 25);
  const currentPeakStatus = Number(activeWeatherResult?.peak_status ?? 0);
  const currentWeatherError = activeWeatherResult?.weather_error || null;
  const currentWeatherTimestamp = activeWeatherResult?.timestamp
    ? new Date(activeWeatherResult.timestamp).toLocaleTimeString()
    : null;

  function formatForecast(result) {
    if (!result) return "—";
    if (result.weather_unavailable) return "Weather unavailable";
    return `${Number(result.forecast_rainfall ?? 0).toFixed(1)} mm / AQI ${Number(result.forecast_aqi ?? 0).toFixed(0)}`;
  }

  function formatCurrentRain(result) {
    if (!result) return "—";
    return `${Number(result.rain ?? 0).toFixed(1)} mm`;
  }

  function formatCurrentAqi(result) {
    if (!result) return "—";
    return Number(result.aqi ?? 0).toFixed(0);
  }

  useEffect(() => {
    document.body.dataset.theme = theme;
    localStorage.setItem("gw_theme_v1", theme);
  }, [theme]);

  useEffect(() => {
    if (auth) setAuthSession(auth);
    else clearAuthSession();
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
  const selectedTier = useMemo(() => {
    return shieldsList.find((s) => s.p_id === selectedShopTier) || shieldsList[0];
  }, [selectedShopTier, shieldsList]);
  const recommendedTier = useMemo(() => {
    if (!riskResult?.recommended_tier) return null;
    return shieldsList.find((s) => s.p_id === riskResult.recommended_tier) || null;
  }, [riskResult?.recommended_tier, shieldsList]);
  const payableAmount = useMemo(() => {
    const activeTierPrice = auth?.active_policy
      ? (shieldsList.find((s) => s.p_id === (auth?.shield || 0))?.price || 0)
      : 0;
    return Math.max(0, (selectedTier?.price || 0) - activeTierPrice);
  }, [auth?.active_policy, auth?.shield, selectedTier, shieldsList]);
  const storeActionLabel = selectedShopTier === (auth?.shield || 0) ? "Renew" : "Upgrade";

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
  const coverageEndText = auth?.policy_end_date ? new Date(auth.policy_end_date).toLocaleString() : "No active weekly coverage";

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
        email: registerForm.email,
        location: data.location,
        income: registerForm.income,
        active: data.active,
        shield: data.shield,
        active_policy: data.active_policy,
        policy_start_date: data.policy_start_date || null,
        policy_end_date: data.policy_end_date || null,
        weekly_earnings: data.weekly_earnings,
        access_token: data.access_token || "",
        trust_score: data.trust_score || 100,
        two_factor_enabled: data.two_factor_enabled ?? false,
        bank_account_linked: data.bank_account_linked ?? false,
        bank_account_masked: data.bank_account_masked || null,
        bank_name: data.bank_name || null,
        bank_account_holder: data.bank_account_holder || null,
        preferred_payout_gateway: data.preferred_payout_gateway || null,
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
        email: data.email,
        location: data.location,
        income: data.income,
        active: data.active,
        shield: data.shield,
        active_policy: data.active_policy,
        policy_start_date: data.policy_start_date || null,
        policy_end_date: data.policy_end_date || null,
        weekly_earnings: data.weekly_earnings,
        access_token: data.access_token || "",
        trust_score: data.trust_score || 100,
        two_factor_enabled: data.two_factor_enabled ?? false,
        bank_account_linked: data.bank_account_linked ?? false,
        bank_account_masked: data.bank_account_masked || null,
        bank_name: data.bank_name || null,
        bank_account_holder: data.bank_account_holder || null,
        preferred_payout_gateway: data.preferred_payout_gateway || null,
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

  async function startTwoFactorSetup() {
    setError(null);
    setApiStatus("Preparing authenticator setup...");
    try {
      const data = await apiPost("/api/v1/workers/2fa/setup", {});
      setTwoFactorSetup(data);
      setTwoFactorCode("");
      setApiStatus("Authenticator secret generated. Add it to your app and confirm with a 6-digit code.");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function confirmTwoFactorEnable() {
    if (!twoFactorCode) return;
    setError(null);
    setApiStatus("Enabling two-factor authentication...");
    try {
      const data = await apiPost("/api/v1/workers/2fa/enable", { otp_code: twoFactorCode });
      setAuth((prev) => ({ ...prev, two_factor_enabled: true }));
      setTwoFactorSetup(null);
      setTwoFactorCode("");
      setApiStatus(data.message || "Two-factor authentication enabled.");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function disableTwoFactor() {
    if (!twoFactorCode) return;
    setError(null);
    setApiStatus("Disabling two-factor authentication...");
    try {
      const data = await apiPost("/api/v1/workers/2fa/disable", { otp_code: twoFactorCode });
      setAuth((prev) => ({ ...prev, two_factor_enabled: false }));
      setTwoFactorSetup(null);
      setTwoFactorCode("");
      setApiStatus(data.message || "Two-factor authentication disabled.");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    }
  }

  async function saveBankAccount() {
    setError(null);
    setApiStatus("Saving bank account...");
    try {
      const data = await apiPost("/api/v1/workers/bank-account", bankForm);
      setBankStatus(data);
      setAuth((prev) => ({
        ...prev,
        bank_account_linked: data.linked,
        bank_account_masked: data.account_masked || null,
        bank_name: data.bank_name || null,
        bank_account_holder: data.account_holder || null,
        preferred_payout_gateway: data.preferred_payout_gateway || null,
      }));
      setBankForm((prev) => ({ ...prev, account_number: "", ifsc: "" }));
      setApiStatus(data.message || "Bank account linked successfully.");
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
    setApiStatus(`Activating coverage for selected shield...`);
    const paymentGateway = "razorpay_test";
    const payload = { 
      worker_id: auth.worker_id, 
      p_id: selectedShopTier,
      risk_score: triggerResult?.risk_score || riskResult?.risk_score || 0.0,
      premium: triggerResult?.risk_score ? shopTier.price * triggerResult.risk_score : shopTier.price,
      days: policyForm.days || 7,
      payment_gateway: paymentGateway,
    };
    try {
      const session = await apiPost("/api/v1/payment/create-session", payload);
      await loadExternalScript("https://checkout.razorpay.com/v1/checkout.js");
      if (!window.Razorpay) {
        throw new Error("Razorpay checkout failed to load.");
      }

      await new Promise((resolve, reject) => {
        const razorpay = new window.Razorpay({
          key: session.key_id,
          amount: Math.round(Number(session.amount || payload.premium) * 100),
          currency: session.currency || "INR",
          name: "Parametric Shield",
          description: session.description,
          order_id: session.order_id,
          prefill: {
            name: session.worker_name || auth.name,
            email: session.worker_email || auth.email,
          },
          theme: { color: "#58A6FF" },
          modal: {
            ondismiss: () => reject(new Error("Razorpay checkout was closed before payment completed.")),
          },
          handler: async (response) => {
            try {
              const final = await apiPost("/api/v1/payment/process", {
                ...payload,
                payment_reference: response.razorpay_payment_id,
                payment_order_id: response.razorpay_order_id,
                payment_signature: response.razorpay_signature,
                payment_status: "captured",
              });
              setAuth(prev => ({
                ...prev,
                shield: selectedShopTier,
                active_policy: true,
                policy_start_date: final.start_date || prev?.policy_start_date || null,
                policy_end_date: final.end_date || prev?.policy_end_date || null,
              }));
              addToast(
                "Razorpay Payment Captured",
                `RAZORPAY ref ${final.payment_reference || response.razorpay_payment_id}`
              );
              setMlForm((p) => ({ ...p, base_price: shopTier.base }));
              setPolicyForm((p) => ({ ...p, base_price: shopTier.base }));
              setApiStatus(final.message || "Coverage activated successfully.");
              resolve(final);
            } catch (verifyError) {
              reject(verifyError);
            }
          },
        });
        razorpay.open();
      });
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
      if (data?.weather_unavailable) {
        setError(`Live weather unavailable: ${data.weather_error || "Open-Meteo request failed."}`);
      } else {
        setError(null);
      }
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
      await runCheckTriggers(data.session_id);
      pollRef.current = setInterval(() => runCheckTriggers(data.session_id), 150_000);
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
  async function runCheckTriggers(sid) {
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
      });
      setTriggerResult(data);
      setLastChecked(new Date());
      setAutoClaimStatus(data.triggered ? "triggered" : "none");
      if (data?.weather_unavailable) {
        setError(`Live weather unavailable: ${data.weather_error || "Open-Meteo request failed."}`);
      } else {
        setError(null);
      }
      if (data.triggered && data.payout > 0) {
        // Assume backend gives us 'is_flagged' via the API if we had it, but we use the claim info
        const flagged = data.message?.includes("under manual review") || data.message?.includes("Flagged");
        if (flagged) {
          addToast("Claim Flagged for Review", data.message);
        } else {
          setGatewayData(data);
          setGatewayOpen(true);
        }
      }
    } catch (e) {
      setAutoClaimStatus("none");
      setError(`Tracker refresh failed: ${String(e?.message || e)}`);
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
    apiLogout();
    setSessionId(null);
    setOnline(false);
    setAuth(null);
    setTab("dashboard");
    resetSession();
  }

  async function handleDeleteAccount() {
    if (!auth || deleteConfirmText.trim() !== auth.email) return;

    stopPolling();
    if (sessionId) {
      apiPost("/api/v1/session/end", {}).catch(() => {});
    }

    setDeleteInFlight(true);
    setError(null);
    setApiStatus("Deleting account and clearing related records...");

    try {
      const data = await apiDelete("/api/v1/workers/me");
      clearAuthSession();
      setSessionId(null);
      setOnline(false);
      setAuth(null);
      setTab("dashboard");
      setDeleteConfirmText("");
      setBankStatus(null);
      setTwoFactorSetup(null);
      setTwoFactorCode("");
      resetSession();
      setApiStatus(null);
      addToast("Account Deleted", data.message || "Your account was removed successfully.");
    } catch (e) {
      setError(String(e?.message || e));
      setApiStatus(null);
    } finally {
      setDeleteInFlight(false);
    }
  }

  const nameInitial = (auth?.name || "U").trim().slice(0, 1).toUpperCase();

  return (
    <div className="gwApp">
      <ParticleSwarm />
      <ToastContainer toasts={toasts} />
      <AnimatePresence>
        {gatewayOpen && (
          <PaymentGatewayModal 
            open={gatewayOpen} 
            triggerData={gatewayData} 
            onSettled={() => {
              setAuth(prev => ({ ...prev, weekly_earnings: (prev.weekly_earnings || 0) + Number(gatewayData.payout) }));
              // Ensure we fetch updated payout history next time Account tab is opened
            }}
            onClose={() => {
              setGatewayOpen(false);
               addToast(`Payout Recorded`, `Payout record ${gatewayData.claim_id || "created"} was stored successfully.`);
            }} 
          />
        )}
      </AnimatePresence>
      <nav className="gwNavbar">
        <div className="gwNavBrand">
          <div className="gwBrandLockup" onClick={() => setTab("dashboard")}>
            <div className="gwAppTitle">Parametric Shield</div>
            <div className="gwSubTitle">Climate cover for gig workers</div>
          </div>
        </div>
        {auth ? (
          <div className="gwNavbarCenter">
            <div className="gwTabGroup gwTabGroupCentered">
              {['dashboard', 'tracker', 'store', 'admin'].map((t, idx) => (
                <button 
                  key={t}
                  className={`gwTabMotionBtn ${tab === t ? "gwTabMotionBtnActive" : ""}`} 
                  onClick={() => setTab(t)}
                >
                  {tab === t && (
                    <motion.div 
                      layoutId="activeTab"
                      className="gwTabActiveBg"
                      transition={{ type: "spring", stiffness: 100, damping: 20 }}
                    >
                      <div className="gwTabActiveLine" />
                    </motion.div>
                  )}
                  <span className="gwNavTabLabel">{t.charAt(0).toUpperCase() + t.slice(1)}</span>
                  {t === 'tracker' && (triggerResult?.triggered || online) ? (
                    <span className="gwMicroCounter">{online ? '1' : '0'}</span>
                  ) : null}
                  <span className="gwNavHint">[{idx + 1}]</span>
                </button>
              ))}
            </div>
          </div>
        ) : null}
        <div className="gwNavControls">
          {auth ? (
            <div className="gwTabGroup gwAccountNavGroup">
              <button 
                className={`gwTabMotionBtn ${tab === "account" ? "gwTabMotionBtnActive" : ""}`} 
                onClick={() => setTab("account")}
              >
                {tab === "account" && (
                  <motion.div 
                    layoutId="activeTab"
                    className="gwTabActiveBg"
                    transition={{ type: "spring", stiffness: 100, damping: 20 }}
                  >
                    <div className="gwTabActiveLine" />
                  </motion.div>
                )}
                Account
                <span className="gwNavHint">Profile</span>
              </button>
            </div>
          ) : null}
          <button
            className="gwChip"
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 12px', gap: 6 }}
            onClick={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
            title="Toggle Theme"
          >
            {theme === "light" ? "Switch to Dark" : "Switch to Light"}
          </button>
        </div>
      </nav>

      <div className="gwContainer">

        {error ? <div className="gwAlert gwAlertBad">{error}</div> : null}
        {apiStatus ? <div className="gwAlert gwAlertWarn">{apiStatus}</div> : null}

        {!auth ? (
          <>
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="gwAuthCard"
            >
              <div className="gwAuthIntro">
                <div className="gwEyebrow">Live Protection Layer</div>
                <div className="gwMuted">Create your account, run a live risk scan, and activate weekly coverage powered by real conditions.</div>
              </div>
              <div className="gwAuthHead" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: 16, marginBottom: 16 }}>
                <div className="gwAuthTitle" style={{ fontSize: 24, fontWeight: 700, letterSpacing: -0.5, marginBottom: 16, textAlign: 'center' }}>Get Protected</div>
                <div className="gwAuthTabs" style={{ display: 'flex', gap: 8, background: 'rgba(0,0,0,0.2)', padding: 4, borderRadius: 999 }}>
                  <button
                    className={authMode === "register" ? "gwTabMotionBtn gwTabMotionBtnActive" : "gwTabMotionBtn"}
                    style={{ flex: 1, justifyContent: 'center' }}
                    onClick={() => setAuthMode("register")}
                  >
                    {authMode === "register" && <motion.div layoutId="authTab" className="gwTabActiveBg" style={{ borderRadius: 999 }} transition={{ type: "spring", stiffness: 400, damping: 25 }} />}
                    Create Account
                  </button>
                  <button 
                    className={authMode === "login" ? "gwTabMotionBtn gwTabMotionBtnActive" : "gwTabMotionBtn"}
                    style={{ flex: 1, justifyContent: 'center' }}
                    onClick={() => setAuthMode("login")}
                  >
                    {authMode === "login" && <motion.div layoutId="authTab" className="gwTabActiveBg" style={{ borderRadius: 999 }} transition={{ type: "spring", stiffness: 400, damping: 25 }} />}
                    Sign In
                  </button>
                </div>
              </div>

              <AnimatePresence mode="popLayout">
                <motion.div
                  key={authMode}
                  initial={{ opacity: 0, x: authMode === 'login' ? 20 : -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: authMode === 'login' ? -20 : 20 }}
                  transition={{ duration: 0.2 }}
                >
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
                      <button className="gwPrimaryBtn" style={{ width: '100%', marginTop: 24, height: 44 }} onClick={handleRegister} disabled={!registerForm.name || !registerForm.location || !registerForm.email || registerForm.password.length < 6}>
                        Get Started
                      </button>
                    </>
                  ) : (
                    <>
                      <label className="gwLabel" style={{ marginTop: 12 }}>
                        Email
                        <input className="gwInput" type="email" value={loginForm.email} onChange={(e) => setLoginForm((p) => ({ ...p, email: e.target.value }))} placeholder="user@example.com" />
                      </label>
                      <label className="gwLabel" style={{ marginTop: 16 }}>
                        Password
                        <input className="gwInput" type="password" value={loginForm.password} onChange={(e) => setLoginForm((p) => ({ ...p, password: e.target.value }))} placeholder="Password" />
                      </label>
                      <label className="gwLabel" style={{ marginTop: 16 }}>
                        Authenticator Code
                        <input className="gwInput" value={loginForm.otp_code} onChange={(e) => setLoginForm((p) => ({ ...p, otp_code: e.target.value.replace(/\D/g, "").slice(0, 6) }))} placeholder="Required only if 2FA is enabled" />
                      </label>
                      <button className="gwPrimaryBtn" style={{ width: '100%', marginTop: 24, height: 44 }} onClick={handleLogin} disabled={!loginForm.email || !loginForm.password}>
                        Proceed to Dashboard
                      </button>
                    </>
                  )}
                </motion.div>
              </AnimatePresence>
            </motion.div>
          </>
        ) : null}

        {auth ? (
          <AnimatePresence mode="wait">
            {tab === "dashboard" ? (
              <motion.div key="dashboard" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.2 }} className="gwPage">
                <div className="gwCard gwGlow gwHeroCard">
                  <div className="gwCardHead">
                    <div className="gwProfileIdentity">
                      <div className="gwCardTitle">Total Secured Earnings</div>
                      <div className="gwBigMoney">
                        <RollingNumber val={totalSecured} />
                      </div>
                      <div className="gwMuted">Weekly Goal: Rs {weeklyGoal.toLocaleString("en-IN")} | Coverage ends: {coverageEndText}</div>
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
                        <div className="gwMuted">{auth?.active_policy ? `Active weekly coverage until ${coverageEndText}` : "No active weekly coverage"}</div>
                      </div>
                      <div className="gwPulseBlock" style={{ gridColumn: "span 2" }}>
                        <div className="gwPulseLabel">Account Integrity / Trust</div>
                        <div className="gwPulseValue" style={{ color: auth?.trust_score >= 80 ? "#24d664" : auth?.trust_score >= 50 ? "#ffbe1e" : "#ff4d8d" }}>
                          {auth?.trust_score ?? 100}/100
                        </div>
                        <div className="gwMuted">{auth?.trust_score >= 80 ? "Good Standing" : "Needs Attention"}</div>
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

                <div className="gwCard gwSurfaceAccent" style={{ marginTop: 16 }}>
                  <div className="gwCardHead">
                    <div className="gwProfileIdentity">
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
                      <div className="gwRow gwActionRow" style={{ marginTop: 12 }}>
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
                      <button className={`gwPrimaryBtn ${apiStatus?.includes('Analyzing') ? 'gwPulseScan' : ''}`} onClick={handleRunML} style={{ marginTop: 0 }}>
                        Run ML Risk Scan
                      </button>
                    </div>
                  )}
                </div>

                <div className="gwCard gwGlow" style={{ marginTop: 16 }}>
                  <div className="gwCardHead">
                    <div className="gwProfileIdentity">
                      <div className="gwCardTitle">Protection Status</div>
                      <div className="gwMuted">{auth?.active_policy ? "Shield active — go to Tracker to start monitoring." : "Purchase a shield in the Store to enable automated protection."}</div>
                    </div>
                    <div className="gwTierPill">Tier: {tier.name}</div>
                  </div>
                  {weatherUnavailable ? (
                    <div className="gwAlert gwAlertWarn" style={{ marginTop: 12 }}>
                      Live weather unavailable. {currentWeatherError || "Open-Meteo request failed, so rain and AQI values may be fallback data."}
                    </div>
                  ) : null}
                  {!weatherUnavailable && activeWeatherResult ? (
                    <div className="gwMuted" style={{ marginTop: 12, fontSize: 12 }}>
                      Live weather loaded{currentWeatherTimestamp ? ` at ${currentWeatherTimestamp}` : ""}.
                    </div>
                  ) : null}
                  <div className="gwInlineStats" style={{ marginTop: 12 }}>
                    <div className="gwStat">
                      <div className="gwStatLabel">RISK SCORE</div>
                      <div className="gwStatValue">
                        {currentRiskScore !== undefined && currentRiskScore !== null ? currentRiskScore.toFixed(2) : "—"}
                      </div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel">FORECAST</div>
                      <div className="gwStatValue">{formatForecast(activeWeatherResult)}</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel">RAINFALL</div>
                      <div className="gwStatValue">{formatCurrentRain(activeWeatherResult)}</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel">AQI</div>
                      <div className="gwStatValue">{formatCurrentAqi(activeWeatherResult)}</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel">EST. LOSS</div>
                      <div className="gwStatValue">{activeWeatherResult ? `₹${currentEstimatedLoss.toFixed(0)}` : "—"}</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel">TEMP / PEAK</div>
                      <div className="gwStatValue">
                        {activeWeatherResult ? `${currentTemperature.toFixed(1)}° ${currentPeakStatus ? "⚡" : "○"}` : "—"}
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

                <div className="gwQuoteContainer">
                  <div className="gwQuoteEngineLabel">
                     <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></svg>
                     Parametric Wisdom
                  </div>
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={quoteIndex}
                      initial={{ opacity: 0, filter: "blur(4px)" }}
                      animate={{ opacity: 1, filter: "blur(0px)" }}
                      exit={{ opacity: 0, filter: "blur(4px)" }}
                      transition={{ duration: 0.8 }}
                      className="gwWisdomQuote"
                    >
                      "{QUOTES[quoteIndex]}"
                    </motion.div>
                  </AnimatePresence>
                </div>
              </motion.div>
            ) : null}

            {tab === "tracker" ? (
              <motion.div key="tracker" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.2 }} className="gwPage">

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
                      <div className="gwTwoCols">
                        <div className="gwMetaLine">
                          <div className="gwMetaLabel">TIME ONLINE</div>
                          <div className="gwMetaValue">{online ? onlineDuration : "00:00"}</div>
                        </div>
                        <div className="gwMetaLine">
                          <div className="gwMetaLabel">NEXT CHECK</div>
                          <div className="gwMetaValue">{online ? "Auto / 2.5 min" : "Offline"}</div>
                        </div>
                      </div>
                      <div className="gwMetaLine" style={{ marginTop: 12 }}>
                        <div className="gwMetaLabel">PROTECTED LIMIT</div>
                        <div className="gwMetaValue">₹{tier.limit}</div>
                      </div>
                      <div className="gwRow" style={{ marginTop: 12 }}>
                        <button
                          className={!online ? "gwPrimaryBtn" : "gwDangerBtn"}
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
                  {triggerResult?.weather_unavailable ? (
                    <div className="gwAlert gwAlertWarn" style={{ marginTop: 10 }}>
                      Live weather unavailable. Open-Meteo request failed during the last check.
                    </div>
                  ) : null}
                  <div className="gwInlineStats" style={{ marginTop: 10 }}>
                    <div className="gwStat">
                      <div className="gwStatLabel gwLabelJutro">
                        <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 2.69l5.66 5.66a8 8 0 11-11.31 0z"/></svg>
                        RAINFALL
                      </div>
                      <div className="gwStatValue" style={{ color: (triggerResult?.rain || 0) > 50 ? "var(--danger)" : (triggerResult?.rain || 0) > 10 ? "var(--warning)" : "var(--text-main)", animation: (triggerResult?.rain || 0) > 50 ? "glowPulse 1.5s infinite" : "none" }}>
                        {triggerResult ? `${triggerResult.rain.toFixed(1)} mm` : "—"}
                      </div>
                      <div className="gwMuted" style={{ fontSize: 10 }}>Alert: &gt;10mm / &gt;50mm</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel gwLabelJutro">
                        <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 14a4 4 0 110-8 4 4 0 010 8z"/></svg>
                        AQI
                      </div>
                      <div className="gwStatValue" style={{ color: (triggerResult?.aqi || 0) > 200 ? "var(--danger)" : (triggerResult?.aqi || 0) > 150 ? "var(--warning)" : "var(--text-main)", animation: (triggerResult?.aqi || 0) > 200 ? "glowPulse 1.5s infinite" : "none" }}>
                        {triggerResult ? triggerResult.aqi.toFixed(0) : "—"}
                      </div>
                      <div className="gwMuted" style={{ fontSize: 10 }}>Alert: &gt;100 / &gt;200</div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel gwLabelJutro">
                        <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                        RISK SCORE
                      </div>
                      <div className="gwStatValue" style={{ color: (triggerResult?.risk_score || 0) >= 0.70 ? "var(--danger)" : (triggerResult?.risk_score || 0) >= 0.45 ? "var(--warning)" : "var(--text-main)"}}>
                        {triggerResult ? (triggerResult.risk_score * 100).toFixed(0) + "/100" : "—"}
                      </div>
                      <div className="gwMuted" style={{ fontSize: 10 }}>
                        {lastChecked ? `${lastChecked.toLocaleTimeString()}` : "Not checked yet"}
                      </div>
                    </div>
                    <div className="gwStat">
                      <div className="gwStatLabel gwLabelJutro">
                        <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 12h18M12 3v18"/></svg>
                        FORECAST / LOC
                      </div>
                      <div className="gwStatValue">
                        {triggerResult
                          ? `${Number(triggerResult.forecast_rainfall || 0).toFixed(1)}mm / ${Number(triggerResult.forecast_aqi || 0).toFixed(0)}`
                          : "â€”"}
                      </div>
                      <div className="gwMuted" style={{ fontSize: 10 }}>
                        {triggerResult ? `Loc risk ${(Number(triggerResult.location_risk || 0) * 100).toFixed(0)}/100` : "Forecast snapshot"}
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
                        <div className="gwMuted" style={{ marginTop: 4, fontSize: 11 }}>
                          ML estimated loss: â‚¹{Number(triggerResult.estimated_loss || 0).toFixed(2)}
                        </div>
                      </div>
                    ) : null}
                  </div>
                  <div className="gwRow" style={{ marginTop: 12 }}>
                    <button
                      className="gwSecondaryBtn"
                      onClick={() => runCheckTriggers(sessionId)}
                      disabled={!online}
                      title="Check live trigger conditions"
                    >
                      Check Live Conditions
                    </button>
                    {triggerResult && triggerResult.risk_score >= 0.45 && (auth?.shield || 0) < (triggerResult.risk_score >= 0.75 ? 3 : 2) ? (
                      <button className="gwSecondaryBtn" onClick={goToStore}>
                        Upgrade Shield
                      </button>
                    ) : null}
                  </div>
                </div>
              </motion.div>
            ) : null}

            {tab === "store" ? (
              <motion.div key="store" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.2 }} className="gwPage">
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

                  <div className="gwStoreSummary">
                    <div className="gwStoreHero">
                      <div>
                        <div className="gwEyebrow">Selected Coverage</div>
                        <div className="gwStoreHeroTitle">{selectedTier.name}</div>
                        <div className="gwMuted">
                          {recommendedTier
                            ? `ML currently recommends ${recommendedTier.name} based on your latest risk scan.`
                            : "Run the ML model to unlock a live recommendation based on weather, hours, and location risk."}
                        </div>
                      </div>
                      <div className="gwStoreHeroPrice">Rs {payableAmount}</div>
                    </div>
                    <div className="gwInlineStats gwStoreStats">
                      <div className="gwStat">
                        <div className="gwStatLabel">Coverage Limit</div>
                        <div className="gwStatValue">Rs {selectedTier.limit}</div>
                      </div>
                      <div className="gwStat">
                        <div className="gwStatLabel">Weekly Base</div>
                        <div className="gwStatValue">Rs {selectedTier.base}</div>
                      </div>
                      <div className="gwStat">
                        <div className="gwStatLabel">Policy Length</div>
                        <div className="gwStatValue">{policyForm.days || 7} days</div>
                      </div>
                      <div className="gwStat">
                        <div className="gwStatLabel">Triggers</div>
                        <div className="gwStatValue">{selectedTier.triggers.length || 0}</div>
                      </div>
                    </div>
                  </div>

                  <div className="gwTierGrid">
                    {shieldsList.filter(t => t.p_id > 0).map((t) => (
                      <div
                        key={t.key}
                        className={t.p_id === (auth?.shield || 0) && auth?.active_policy ? "gwTierCard gwTierCardActive" : selectedShopTier === t.p_id ? "gwTierCard" : "gwTierCard"}
                        style={{ 
                          borderColor: t.p_id === (auth?.shield || 0) && auth?.active_policy ? "var(--accent)" : selectedShopTier === t.p_id ? "var(--border)" : "var(--border)",
                          boxShadow: t.p_id === (auth?.shield || 0) && auth?.active_policy ? "0 0 0 1px var(--accent), var(--shadow-md)" : "none"
                        }}
                      >
                        {t.p_id === (auth?.shield || 0) && auth?.active_policy ? <div className="gwBadge" style={{ background: "var(--accent)", color: "#fff" }}>ACTIVE PLATFORM</div> : t.popular ? <div className="gwBadge">MOST POPULAR</div> : null}
                        {riskResult?.recommended_tier === t.p_id ? (
                          <div className="gwBadge" style={{ 
                            right: t.popular || (t.p_id === (auth?.shield || 0) && auth?.active_policy) ? 140 : 12, 
                            background: "rgba(88,166,255,.15)", 
                            color: "var(--accent)", 
                            borderColor: "rgba(88,166,255,.3)" 
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

                  <div className="gwRow gwStoreFooter" style={{ marginTop: 16 }}>
                    <div className="gwMuted" style={{ fontSize: 12 }}>
                      {gatewayCatalog.payment_gateways.find((gateway) => gateway.code === "razorpay_test")?.description || "Payment is processed through Razorpay checkout."}
                    </div>
                  </div>
                  <div className="gwRow gwStoreFooter" style={{ marginTop: 16 }}>
                    <button className="gwPrimaryBtn" onClick={payForShield} disabled={(selectedShopTier < (auth?.shield || 0)) || (selectedShopTier === (auth?.shield || 0) && auth?.active_policy)}>
                      Pay Rs {payableAmount} to {storeActionLabel}
                    </button>
                  </div>

                  <div className="gwDivider" style={{ marginTop: 16 }} />

                  <div className="gwMuted" style={{ fontSize: 12 }}>
                     Tip: Run ML Model after selecting tier, then Buy Policy.
                  </div>
                </div>
              </motion.div>
            ) : null}

            {tab === "admin" ? (
              <AdminDashboard />
            ) : null}

            {tab === "account" ? (
              <motion.div key="account" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.2 }} className="gwPage">
                <div className="gwCard gwGlow">
                  
                  <div className="gwProfileHeader">
                    <div className="gwAvatar" style={{ width: 80, height: 80, fontSize: 32, flexShrink: 0, boxShadow: '0 0 0 2px var(--accent)' }}>{nameInitial}</div>
                    <div>
                      <div className="gwAccountName gwAccountNameLarge">{auth.name}</div>
                      <div className="gwMuted" style={{ fontSize: 13, marginTop: 4 }}>{auth.email} • {auth.location}</div>
                      <div className="gwBadgeRow gwAccountBadgeRow">
                        <span className="gwStatusBadge gwStatusBadgeSuccess">KYC Verified</span>
                        <span className={`gwStatusBadge ${auth?.trust_score >= 80 ? "gwStatusBadgeSuccess" : auth?.trust_score >= 50 ? "gwStatusBadgeWarn" : "gwStatusBadgeDanger"}`}>
                          TRUST SCORE: {auth?.trust_score ?? 100}/100
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="gwAuthTabs" style={{ display: 'flex', gap: 8, background: 'rgba(0,0,0,0.2)', padding: 4, borderRadius: 999, marginBottom: 24 }}>
                    <button className={accountTab === "active" ? "gwTabMotionBtn gwTabMotionBtnActive" : "gwTabMotionBtn"} style={{ flex: 1, justifyContent: 'center' }} onClick={() => setAccountTab("active")}>
                      {accountTab === "active" && <motion.div layoutId="accountTabId" className="gwTabActiveBg" style={{ borderRadius: 999 }} transition={{ type: "spring", stiffness: 400, damping: 25 }} />}
                      Active Policies
                    </button>
                    <button className={accountTab === "recent" ? "gwTabMotionBtn gwTabMotionBtnActive" : "gwTabMotionBtn"} style={{ flex: 1, justifyContent: 'center' }} onClick={() => setAccountTab("recent")}>
                      {accountTab === "recent" && <motion.div layoutId="accountTabId" className="gwTabActiveBg" style={{ borderRadius: 999 }} transition={{ type: "spring", stiffness: 400, damping: 25 }} />}
                      Instant Payout History
                    </button>
                  </div>

                  {accountTab === "active" ? (
                    <>
                      <div className="gwTwoCols gwAccountSummaryGrid" style={{ gap: 24 }}>
                        <div className="gwSettingsPanel">
                          <div className="gwCardTitle" style={{ marginBottom: 16 }}>Financial Summary</div>
                          <div className="gwMetaLine" style={{ margin: '12px 0' }}>
                            <div className="gwMetaLabel gwLabelJutro">TOTAL SECURED</div>
                            <div className="gwMetaValue" style={{ fontWeight: 700, fontSize: 16 }}>₹{Number(totalSecured).toFixed(0)}</div>
                          </div>
                          <div className="gwMetaLine" style={{ margin: '12px 0' }}>
                            <div className="gwMetaLabel gwLabelJutro">DAILY INCOME</div>
                            <div className="gwMetaValue gwMuted">₹{auth.income}/day</div>
                          </div>
                        </div>

                        <div className="gwSettingsPanel">
                          <div className="gwCardTitle" style={{ marginBottom: 16 }}>Protection State</div>
                          <div className="gwMetaLine" style={{ margin: '12px 0' }}>
                            <div className="gwMetaLabel gwLabelJutro">ACTIVE TIER</div>
                            <div className="gwMetaValue" style={{ color: 'var(--accent)', fontWeight: 600 }}>{tier.name}</div>
                          </div>
                          <div className="gwMetaLine" style={{ margin: '12px 0' }}>
                            <div className="gwMetaLabel gwLabelJutro">COVERAGE LIMIT</div>
                            <div className="gwMetaValue">₹{tier.limit}</div>
                          </div>
                          <div className="gwMetaLine" style={{ margin: '12px 0' }}>
                            <div className="gwMetaLabel gwLabelJutro">ACTIVE WEEKLY COVERAGE</div>
                            <div className="gwMetaValue gwMuted">{coverageEndText}</div>
                          </div>
                        </div>
                      </div>

                      <div className="gwDivider" style={{ margin: '24px 0' }} />

                      <div className="gwCardTitle" style={{ marginBottom: 16 }}>Security & Preferences</div>
                      
                      <div className="gwSettingsGrid">
                        <div className="gwListItem gwSettingsPanel" style={{ display: 'block' }}>
                          <div>
                            <strong>Two-Factor Authentication</strong>
                            <div className="gwMuted" style={{ fontSize: 11 }}>
                              {accountSettingsLoading
                                ? "Checking live 2FA status..."
                                : auth?.two_factor_enabled
                                  ? "Enabled. Login now requires your authenticator code."
                                  : "2FA not found. Protect your account with a 6-digit authenticator code."}
                            </div>
                          </div>
                          {twoFactorSetup ? (
                            <div style={{ marginTop: 12 }}>
                              <div className="gwMuted" style={{ fontSize: 11 }}>Manual key</div>
                              <div style={{ fontFamily: "monospace", wordBreak: "break-all", marginTop: 4 }}>{twoFactorSetup.manual_entry_key}</div>
                              <div className="gwMuted" style={{ fontSize: 11, marginTop: 8 }}>Paste this into Google Authenticator, Microsoft Authenticator, or Authy.</div>
                            </div>
                          ) : null}
                          <div className="gwRow gwActionRow" style={{ marginTop: 12, gap: 12, alignItems: "center" }}>
                            <input
                              className="gwInput"
                              style={{ maxWidth: 220 }}
                              value={twoFactorCode}
                              onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                              placeholder="6-digit code"
                            />
                            {auth?.two_factor_enabled ? (
                              <button className="gwSecondaryBtn" style={{ padding: "8px 14px", fontSize: 12 }} onClick={disableTwoFactor}>
                                Disable 2FA
                              </button>
                            ) : twoFactorSetup ? (
                              <button className="gwPrimaryBtn" style={{ padding: "8px 14px", fontSize: 12 }} onClick={confirmTwoFactorEnable}>
                                Confirm 2FA
                              </button>
                            ) : (
                              <button className="gwSecondaryBtn" style={{ padding: "8px 14px", fontSize: 12 }} onClick={startTwoFactorSetup}>
                                Setup 2FA
                              </button>
                            )}
                          </div>
                        </div>
                        <div className="gwListItem gwSettingsPanel" style={{ display: 'block' }}>
                          <div>
                            <strong>Linked Bank Account</strong>
                            <div className="gwMuted" style={{ fontSize: 11 }}>
                              {accountSettingsLoading
                                ? "Checking linked bank account..."
                                : bankStatus?.linked || auth?.bank_account_linked
                                  ? `${bankStatus?.bank_name || auth?.bank_name || "Bank"} ${bankStatus?.account_masked || auth?.bank_account_masked || ""}`
                                  : "Bank account not found. Add payout details for transfers."}
                            </div>
                          </div>
                          <div className="gwTwoCols gwBankGrid" style={{ gap: 12, marginTop: 12 }}>
                            <label className="gwLabel">
                              Account holder
                              <input className="gwInput" value={bankForm.account_holder} onChange={(e) => setBankForm((p) => ({ ...p, account_holder: e.target.value }))} />
                            </label>
                            <label className="gwLabel">
                              Bank name
                              <input className="gwInput" value={bankForm.bank_name} onChange={(e) => setBankForm((p) => ({ ...p, bank_name: e.target.value }))} />
                            </label>
                            <label className="gwLabel">
                              Account number
                              <input className="gwInput" value={bankForm.account_number} onChange={(e) => setBankForm((p) => ({ ...p, account_number: e.target.value.replace(/\D/g, "") }))} />
                            </label>
                            <label className="gwLabel">
                              IFSC
                              <input className="gwInput" value={bankForm.ifsc} onChange={(e) => setBankForm((p) => ({ ...p, ifsc: e.target.value.toUpperCase() }))} />
                            </label>
                            <label className="gwLabel">
                              Instant payout gateway
                              <select className="gwInput" value={bankForm.preferred_payout_gateway} onChange={(e) => setBankForm((p) => ({ ...p, preferred_payout_gateway: e.target.value }))}>
                                {(gatewayCatalog.payout_gateways || []).map((gateway) => (
                                  <option key={gateway.code} value={gateway.code}>
                                    {gateway.name}
                                  </option>
                                ))}
                              </select>
                            </label>
                          </div>
                          <div className="gwRow gwActionRow" style={{ marginTop: 12, gap: 12, alignItems: "center" }}>
                            <button
                              className="gwSecondaryBtn"
                              style={{ padding: "8px 14px", fontSize: 12 }}
                              onClick={saveBankAccount}
                              disabled={!bankForm.account_holder || !bankForm.bank_name || !bankForm.account_number || !bankForm.ifsc}
                            >
                              Save Bank Account
                            </button>
                            {bankStatus?.verified || auth?.bank_account_linked ? (
                              <div className="gwMuted" style={{ fontSize: 11 }}>
                                Verified for payouts: {bankStatus?.account_masked || auth?.bank_account_masked} via {(bankStatus?.preferred_payout_gateway || auth?.preferred_payout_gateway || bankForm.preferred_payout_gateway || "upi_simulator").toUpperCase()}
                              </div>
                            ) : !accountSettingsLoading ? (
                              <div className="gwMuted" style={{ fontSize: 11 }}>
                                No linked bank account found yet.
                              </div>
                            ) : null}
                          </div>
                        </div>
                      </div>

                      <div className="gwRow gwActionRow" style={{ marginTop: 24, justifyContent: 'flex-start', gap: 12 }}>
                        <button className="gwSecondaryBtn" onClick={handleLogout}>Logout Securely</button>
                      </div>

                      <div className="gwDangerZone">
                        <div className="gwDangerZoneHead">
                          <div>
                            <div className="gwCardTitle">Delete Account</div>
                            <div className="gwMuted" style={{ fontSize: 12, marginTop: 6 }}>
                              This permanently removes your worker profile, policy, payouts, bank details, and live session history.
                            </div>
                          </div>
                          <span className="gwStatusBadge gwStatusBadgeDanger">Danger Zone</span>
                        </div>
                        <div className="gwDangerZoneForm">
                          <label className="gwLabel">
                            Confirm with your email
                            <input
                              className="gwInput"
                              value={deleteConfirmText}
                              onChange={(e) => setDeleteConfirmText(e.target.value)}
                              placeholder={auth.email}
                            />
                          </label>
                          <button
                            className="gwDangerBtn"
                            onClick={handleDeleteAccount}
                            disabled={deleteInFlight || deleteConfirmText.trim() !== auth.email}
                            title="Type your account email exactly to enable deletion"
                          >
                            {deleteInFlight ? "Deleting Account..." : "Delete Account Permanently"}
                          </button>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="gwList">
                      {payoutHistory.length === 0 ? (
                         <div className="gwMuted" style={{ padding: 16, textAlign: 'center' }}>No recent payouts.</div>
                      ) : (
                         payoutHistory.map(p => (
                           <div key={p.payout_id} className="gwListItem" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                             <div>
                               <div style={{ fontWeight: 600 }}>{(p.trigger_type || "UNKNOWN").toUpperCase()} EVENT DETECTED</div>
                               <div className="gwMuted" style={{ fontSize: 12, marginTop: 4 }}>
                                 {new Date(p.timestamp).toLocaleString()} • TXN: {(p.idempotency_key || p.payout_id).substring(0, 8).toUpperCase()}...
                               </div>
                               <div className="gwMuted" style={{ fontSize: 11, marginTop: 4 }}>
                                 {(p.transfer_status || "queued").toUpperCase()} via {(p.payout_gateway || "upi_simulator").toUpperCase()} • Ref {p.payout_reference || "Pending"}
                               </div>
                               {p.is_flagged ? (
                                  <div style={{ marginTop: 6, fontSize: 11, color: "var(--warning)" }}>FLAGGED: MANUAL REVIEW</div>
                                ) : (
                                  <div style={{ marginTop: 6, fontSize: 11, color: "var(--success)" }}>
                                    ✓ {p.transfer_status === "requires_bank_account" ? "BANK DETAILS REQUIRED" : "SECURE TRANSFER SUCCESS"}
                                    {p.beneficiary_masked ? ` • ${p.beneficiary_masked}` : ""}
                                  </div>
                                )}
                             </div>
                             <div className="gwBigMoney" style={{ marginTop: 0, fontSize: 18, color: p.is_flagged ? "var(--warning)" : "var(--success)" }}>
                               ₹{p.amount}
                             </div>
                           </div>
                         ))
                      )}
                    </div>
                  )}

                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>
        ) : null}

      </div>
    </div>
  );
}
