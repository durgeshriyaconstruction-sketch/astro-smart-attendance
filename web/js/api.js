// Thin Supabase client: password sign-in, silent refresh, RPC and REST.
// No SDK, so the whole app is three files and a stylesheet, and nothing on the
// page can drift from the database contract.
import { CONFIG } from './config.js';

const SESSION_KEY = 'astro.session.v1';
let session = null;

function loadSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    session = raw ? JSON.parse(raw) : null;
  } catch {
    session = null;
  }
  return session;
}

function saveSession(next) {
  session = next;
  if (next) localStorage.setItem(SESSION_KEY, JSON.stringify(next));
  else localStorage.removeItem(SESSION_KEY);
}

loadSession();

export function signedIn() {
  return Boolean(session?.access_token);
}

export function sessionUser() {
  return session?.user || null;
}

async function parseError(res) {
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* empty body */
  }
  const message =
    body?.message || body?.error_description || body?.msg || body?.error || `HTTP ${res.status}`;
  const err = new Error(String(message));
  err.status = res.status;
  err.detail = body?.details || body?.hint || '';
  err.code = body?.code || '';
  if (res.status === 401 || /JWT|token/i.test(String(message))) err.auth = true;
  return err;
}

async function raw(path, { method = 'GET', body, headers = {}, auth = true } = {}) {
  const url = `${CONFIG.url}${path}`;
  const send = (token) => {
    const h = { apikey: CONFIG.key, ...headers };
    if (body !== undefined) h['Content-Type'] = 'application/json';
    if (auth && token) h.Authorization = `Bearer ${token}`;
    return fetch(url, {
      method,
      headers: h,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  };

  let res = await send(session?.access_token);
  if (res.status === 401 && auth && session?.refresh_token) {
    try {
      await refreshSession();
      res = await send(session.access_token);
    } catch {
      saveSession(null);
      throw await parseError(res);
    }
  }
  return res;
}

// --------------------------------------------------------------- auth -----

function storeToken(payload) {
  if (!payload?.access_token) throw new Error('Sign-in did not return a token');
  const ms = Number(payload.expires_in || 3600) * 1000;
  saveSession({
    access_token: payload.access_token,
    refresh_token: payload.refresh_token,
    expires_at: Date.now() + ms,
    user: payload.user || session?.user || null,
  });
}

export async function signIn(email, password) {
  const res = await fetch(`${CONFIG.url}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: { apikey: CONFIG.key, 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: String(email).trim(), password }),
  });
  if (!res.ok) throw await parseError(res);
  storeToken(await res.json());
  return session.user;
}

export async function refreshSession() {
  if (!session?.refresh_token) throw new Error('No session');
  const res = await fetch(`${CONFIG.url}/auth/v1/token?grant_type=refresh_token`, {
    method: 'POST',
    headers: { apikey: CONFIG.key, 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: session.refresh_token }),
  });
  if (!res.ok) {
    saveSession(null);
    throw await parseError(res);
  }
  storeToken(await res.json());
}

export async function ensureFreshSession() {
  if (!session) return;
  if (Date.now() < (session.expires_at || 0) - CONFIG.refreshSkewMs) return;
  try {
    await refreshSession();
  } catch {
    saveSession(null);
    throw new Error('Session expired — please sign in again');
  }
}

export async function signOut() {
  const token = session?.access_token;
  saveSession(null);
  if (token) {
    // best effort: revoke server-side too
    fetch(`${CONFIG.url}/auth/v1/logout`, {
      method: 'POST',
      headers: { apikey: CONFIG.key, Authorization: `Bearer ${token}` },
    }).catch(() => {});
  }
}

export async function changePassword(newPassword) {
  const res = await raw('/auth/v1/user', {
    method: 'PUT',
    body: { password: newPassword },
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw await parseError(res);
  return res.json();
}

// ----------------------------------------------------------------- rpc ----

export async function rpc(name, args = {}) {
  await ensureFreshSession();
  const res = await raw(`/rest/v1/rpc/${name}`, { method: 'POST', body: args });
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return null;
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

// ---------------------------------------------------------------- rest ----

export async function rest(path, { method = 'GET', body, prefer = 'return=representation' } = {}) {
  await ensureFreshSession();
  const res = await raw(`/rest/v1/${path}`, {
    method,
    body,
    headers: prefer ? { Prefer: prefer } : {},
  });
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return null;
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export const q = (params) =>
  Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&');
