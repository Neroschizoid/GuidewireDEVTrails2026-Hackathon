const AUTH_KEY = "gw_worker_auth_v1";

let accessTokenMemory = null;

function readStoredSession() {
  try {
    const raw = sessionStorage.getItem(AUTH_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeStoredSession(session) {
  try {
    if (session) sessionStorage.setItem(AUTH_KEY, JSON.stringify(session));
    else sessionStorage.removeItem(AUTH_KEY);
  } catch {
    // ignore storage failures
  }
}

export function getStoredAuth() {
  return readStoredSession();
}

export function getTokens() {
  return {
    accessToken: accessTokenMemory,
  };
}

export function setAuthSession(auth) {
  if (!auth) {
    clearAuthSession();
    return;
  }

  accessTokenMemory = auth.access_token || null;

  writeStoredSession({
    worker_id: auth.worker_id || "",
    name: auth.name || "",
    email: auth.email || "",
    location: auth.location || "",
    income: auth.income || 0,
    active: auth.active ?? false,
    shield: auth.shield || 0,
    active_policy: auth.active_policy ?? false,
    policy_start_date: auth.policy_start_date || null,
    policy_end_date: auth.policy_end_date || null,
    weekly_earnings: auth.weekly_earnings || 0,
    trust_score: auth.trust_score || 100,
    two_factor_enabled: auth.two_factor_enabled ?? false,
    bank_account_linked: auth.bank_account_linked ?? false,
    bank_account_masked: auth.bank_account_masked || null,
    bank_name: auth.bank_name || null,
    bank_account_holder: auth.bank_account_holder || null,
    preferred_payout_gateway: auth.preferred_payout_gateway || null,
  });
}

export function setAccessToken(accessToken) {
  accessTokenMemory = accessToken || null;
}

export function clearAuthSession() {
  accessTokenMemory = null;
  writeStoredSession(null);
}
