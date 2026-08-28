const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string
  ) {
    super(message);
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

export function accessToken() {
  return activeAccessToken;
}

export function currentUser() {
  return activeUser;
}

export function clearSession() {
  activeAccessToken = null;
  activeUser = null;
}

export async function login(input: { email: string; password: string; workspace_id?: string }) {
  const response = await rawRequest<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input)
  });
  storeSession(response);
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
  storeSession(response);
  return response;
}

export async function beginSso(provider: "google" | "linkedin", intent: "login" | "signup") {
  return rawRequest<{ authorization_url: string }>(
    `/api/v1/auth/sso/${provider}/start?intent=${intent}`
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
    await rawRequest("/api/v1/auth/logout", { method: "POST" });
  } finally {
    clearSession();
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    return await rawRequest<T>(path, init);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401 || !accessToken()) throw error;
    refreshInFlight ??= refreshSession().finally(() => {
      refreshInFlight = null;
    });
    if (!(await refreshInFlight)) throw error;
    return rawRequest<T>(path, init);
  }
}

async function rawRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const token = activeAccessToken;
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers
    }
  });
  const payload = await response.json().catch(() => ({}));
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
    storeSession(response);
    return true;
  } catch {
    clearSession();
    return false;
  }
}

function storeSession(response: AuthResponse) {
  activeAccessToken = response.access_token;
  activeUser = response.user;
}
