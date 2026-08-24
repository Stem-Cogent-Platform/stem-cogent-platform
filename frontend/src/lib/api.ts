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

export function accessToken() {
  return typeof window === "undefined" ? null : window.sessionStorage.getItem("sc_access_token");
}

export function clearSession() {
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem("sc_access_token");
    window.sessionStorage.removeItem("sc_user");
  }
}

export async function login(input: { workspace_id: string; email: string; password: string }) {
  const response = await rawRequest<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input)
  });
  storeSession(response);
  return response;
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
  const token = typeof window === "undefined" ? null : window.sessionStorage.getItem("sc_access_token");
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
  window.sessionStorage.setItem("sc_access_token", response.access_token);
  window.sessionStorage.setItem("sc_user", JSON.stringify(response.user));
}
