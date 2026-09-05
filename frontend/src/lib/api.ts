const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type AuthResponse = {
  access_token: string;
  expires_in: number;
  user: Record<string, unknown>;
};

let refreshInFlight: Promise<boolean> | null = null;
let activeAccessToken: string | null = null;
let activeUser: Record<string, unknown> | null = null;
let activeSessionOrigin = "";

export function accessToken() {
  return activeAccessToken;
}

export function currentUser() {
  return activeUser;
}

export function clearSession() {
  activeAccessToken = null;
  activeUser = null;
  activeSessionOrigin = "";
}

export async function login(input: { email: string; password: string; workspace_id?: string }) {
  const response = await rawRequest<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input)
  });
  storeSession(response, "");
  return response;
}

export async function register(input: {
  company_name: string;
  display_name: string;
  email: string;
  password: string;
}) {
  const response = await rawRequest<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(input)
  });
  storeSession(response, "");
  return response;
}

export async function adminMfaLogin(input: {
  email: string;
  password: string;
  totp_code: string;
  workspace_id?: string;
}) {
  const response = await rawRequest<AuthResponse>("/api/v1/auth/admin/mfa", {
    method: "POST",
    body: JSON.stringify(input)
  });
  storeSession(response, "");
  return response;
}

export async function validateInvitation(token: string) {
  return rawRequest<{ valid: true; workspace_name: string; email: string; expires_at: string }>(
    `/api/v1/auth/invitations/validate?token=${encodeURIComponent(token)}`
  );
}

export async function acceptInvitation(input: { token: string; display_name: string; password: string }) {
  const response = await rawRequest<AuthResponse>("/api/v1/auth/invitations/accept", {
    method: "POST",
    body: JSON.stringify(input)
  });
  storeSession(response, "");
  return response;
}

export type ProductEventName =
  | "SESSION_STARTED" | "BRIEFING_VIEWED" | "BRIEF_OPENED" | "BRIEF_UPDATED_VIEWED"
  | "EVIDENCE_PANEL_OPENED" | "CIL_OPENED" | "CIL_QUERY_SUBMITTED"
  | "BRIEF_ACKNOWLEDGED" | "BRIEF_WATCHED" | "BRIEF_ESCALATED" | "BRIEF_ACTED_ON"
  | "BRIEF_DISMISSED" | "WIDER_INTELLIGENCE_VIEWED" | "WATCHLIST_ITEM_VIEWED"
  | "FOCUS_AREA_ADDED" | "FOCUS_AREA_UPDATED" | "SEARCH_PERFORMED" | "ALERT_OPENED"
  | "DIGEST_OPENED" | "DECISION_PATHS_VIEWED";

export async function recordProductEvent(
  eventName: ProductEventName,
  input: { object_type?: string; object_id?: string; metadata?: Record<string, string | number | boolean> } = {}
) {
  try {
    await apiRequest("/api/v1/events", {
      method: "POST",
      body: JSON.stringify({ event_name: eventName, ...input })
    });
  } catch {
    // Analytics is deliberately non-blocking; primary product actions still complete.
  }
}

export async function beginSso(provider: "google" | "linkedin", intent: "login" | "signup") {
  return rawRequest<{ authorization_url: string }>(
    `${API_ORIGIN}/api/v1/auth/sso/${provider}/start?intent=${intent}`
  );
}

export async function bootstrapSession() {
  if (activeAccessToken && activeUser) return true;
  refreshInFlight ??= refreshSession().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export async function logout() {
  try {
    await rawRequest(`${activeSessionOrigin}/api/v1/auth/logout`, { method: "POST" });
  } finally {
    clearSession();
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  if (!activeAccessToken) {
    refreshInFlight ??= refreshSession().finally(() => {
      refreshInFlight = null;
    });
    if (!(await refreshInFlight)) {
      throw new ApiError("Your session has expired. Sign in again.", 401, "SESSION_REQUIRED");
    }
  }
  try {
    return await rawRequest<T>(path, init);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    refreshInFlight ??= refreshSession().finally(() => {
      refreshInFlight = null;
    });
    if (!(await refreshInFlight)) throw error;
    return rawRequest<T>(path, init);
  }
}

async function rawRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const token = activeAccessToken;
  const requestId = globalThis.crypto?.randomUUID?.() ?? `stem-${Date.now().toString(36)}`;
  let response: globalThis.Response;
  try {
    response = await fetch(path, {
      ...init,
      credentials: "include",
      signal: init?.signal ?? AbortSignal.timeout(20_000),
      headers: {
        Accept: "application/json",
        "X-Request-ID": requestId,
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers
      }
    });
  } catch (error) {
    const timedOut = error instanceof DOMException && error.name === "TimeoutError";
    throw new ApiError(
      timedOut
        ? "The intelligence service took too long to respond. Please try again."
        : "Stem could not reach the intelligence service. Check your connection and try again.",
      0,
      timedOut ? "REQUEST_TIMEOUT" : "NETWORK_UNAVAILABLE"
    );
  }
  const isEmpty = response.status === 204 || response.headers.get("content-length") === "0";
  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
  if (response.ok && !isEmpty && !contentType.includes("application/json")) {
    throw new ApiError(
      "The intelligence service returned an invalid response. Please try again.",
      response.status,
      "INVALID_API_RESPONSE"
    );
  }
  const payload = isEmpty ? {} : await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message ?? "We could not complete that request. Please try again.";
    throw new ApiError(message, response.status, detail?.code);
  }
  return payload as T;
}

async function refreshSession() {
  try {
    const response = await rawRequest<AuthResponse>("/api/v1/auth/refresh", { method: "POST" });
    storeSession(response, "");
    return true;
  } catch {
    try {
      const response = await rawRequest<AuthResponse>(`${API_ORIGIN}/api/v1/auth/refresh`, { method: "POST" });
      storeSession(response, API_ORIGIN);
      return true;
    } catch {
      clearSession();
      return false;
    }
  }
}

function storeSession(response: AuthResponse, sessionOrigin = "") {
  activeAccessToken = response.access_token;
  activeUser = response.user;
  activeSessionOrigin = sessionOrigin;
}
