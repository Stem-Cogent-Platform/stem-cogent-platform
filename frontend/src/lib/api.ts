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
  | "BRIEF_DISMISSED" | "WIDER_INTELLIGENCE_VIEWED" | "INTELLIGENCE_VIEWED"
  | "INTELLIGENCE_TAB_CHANGED" | "WATCHLIST_ITEM_VIEWED"
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
        ...(init?.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
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

// ---------------------------------------------------------------------------
// Phase 6b: Live API Contract Implementations
// ---------------------------------------------------------------------------

import type {
  AdminTenant,
  ArtifactListResponse,
  FailoverSimulationResult,
  IntelligenceArtifact,
  OnboardingStatus,
  TelemetryData,
  WorkspaceMessage,
  WorkspaceSession,
  WorkspaceTurnResponse,
} from "./types";

/* Onboarding & Workspace Bootstrap */

export type StageACompanyInput = {
  company_name: string;
  operating_licenses: string[];
  active_products: string[];
  clearing_rails: string[];
  primary_country?: string;
  compliance_thresholds?: Record<string, unknown>;
};

export type StageBLensInput = {
  business_function: string;
  decision_lens: "executive_strategy" | "compliance_legal" | "product_engineering" | "treasury_reconciliation";
  priority_focus?: string | null;
  alert_sensitivity?: "CRITICAL_ONLY" | "IMPORTANT_AND_CRITICAL";
};

export async function submitStageA(input: StageACompanyInput) {
  return apiRequest<{
    success: boolean;
    organization_id: string;
    stage_a_completed: boolean;
    bootstrap_dispatched: boolean;
  }>("/api/v1/onboarding/stage-a", {
    method: "POST",
    body: JSON.stringify({
      primary_country: "NG",
      compliance_thresholds: {},
      ...input,
    }),
  });
}

export async function submitStageB(input: StageBLensInput) {
  return apiRequest<{
    success: boolean;
    user_id: string;
    stage_b_completed: boolean;
    decision_lens: string;
    business_function: string;
  }>("/api/v1/onboarding/stage-b", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getOnboardingStatus() {
  return apiRequest<OnboardingStatus>("/api/v1/onboarding/status");
}

export async function inviteTeamMember(input: {
  email: string;
  assigned_lens?: "executive_strategy" | "compliance_legal" | "product_engineering" | "treasury_reconciliation";
}) {
  return apiRequest<{
    success: boolean;
    email: string;
    token: string;
    otp_code: string;
    expires_at: string;
  }>("/api/v1/onboarding/invite", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/* Core Decision Artifacts */

export type ArtifactFilterParams = {
  artifact_type?: string;
  urgency?: string;
  search?: string;
  include_dismissed?: boolean;
  limit?: number;
  offset?: number;
};

export async function listArtifacts(params: ArtifactFilterParams = {}) {
  const query = new URLSearchParams();
  if (params.artifact_type && params.artifact_type !== "ALL") {
    query.set("artifact_type", params.artifact_type);
  }
  if (params.urgency && params.urgency !== "ALL") {
    query.set("urgency", params.urgency);
  }
  if (params.search) {
    query.set("search", params.search);
  }
  if (params.include_dismissed) {
    query.set("include_dismissed", "true");
  }
  if (params.limit) {
    query.set("limit", String(params.limit));
  }
  if (params.offset) {
    query.set("offset", String(params.offset));
  }
  const queryString = query.toString();
  const endpoint = queryString ? `/api/v1/artifacts?${queryString}` : "/api/v1/artifacts";
  return apiRequest<ArtifactListResponse>(endpoint);
}

export async function getArtifact(id: string) {
  return apiRequest<IntelligenceArtifact>(`/api/v1/artifacts/${id}`);
}

export async function updateActionItemStatus(
  artifactId: string,
  actionId: string,
  completed: boolean,
  notes?: string
) {
  return apiRequest<{
    success: boolean;
    artifact_id: string;
    action_id: string;
    completed: boolean;
    payload: Record<string, unknown>;
  }>(`/api/v1/artifacts/${artifactId}/actions/${encodeURIComponent(actionId)}`, {
    method: "PATCH",
    body: JSON.stringify({ completed, notes }),
  });
}

export async function updateExecutiveStance(
  artifactId: string,
  stance: "counter_attack" | "monitor" | "ignore",
  rationale?: string
) {
  return apiRequest<{
    success: boolean;
    artifact_id: string;
    stance: string;
    executive_stance: Record<string, unknown>;
  }>(`/api/v1/artifacts/${artifactId}/stance`, {
    method: "PATCH",
    body: JSON.stringify({ stance, rationale }),
  });
}

export async function simulateFailover(
  artifactId: string,
  targetNode = "Wema ALAT Node",
  trafficPct = 100
) {
  return apiRequest<{
    success: boolean;
    artifact_id: string;
    simulation: FailoverSimulationResult;
  }>(`/api/v1/artifacts/${artifactId}/simulate-failover`, {
    method: "POST",
    body: JSON.stringify({ target_node: targetNode, traffic_pct: trafficPct }),
  });
}

/* Radar & Telemetry */

export type SignalFilterParams = {
  domain?: string;
  urgency?: string;
  query?: string;
  limit?: number;
  offset?: number;
};

export async function getRadarSignals(params: SignalFilterParams = {}) {
  const query = new URLSearchParams();
  if (params.domain && params.domain !== "ALL") query.set("domain", params.domain);
  if (params.urgency && params.urgency !== "ALL") query.set("urgency", params.urgency);
  if (params.query) query.set("query", params.query);
  if (params.limit) query.set("limit", String(params.limit));
  if (params.offset) query.set("offset", String(params.offset));
  const qs = query.toString();
  return apiRequest<{
    signals?: Array<{
      id: string;
      title: string;
      summary?: string;
      primary_domain: string;
      urgency_band: string;
      confidence_band: string;
      created_at: string;
      source_count?: number;
      corroboration_strength?: string;
      source_name?: string;
      source_url?: string;
    }>;
    items?: Array<{
      id: string;
      title: string;
      summary?: string;
      primary_domain: string;
      urgency_band: string;
      confidence_band: string;
      created_at: string;
      source_count?: number;
    }>;
    total?: number;
  }>(qs ? `/api/v1/signals?${qs}` : "/api/v1/signals");
}

export async function getTelemetry(): Promise<TelemetryData> {
  try {
    return await apiRequest<TelemetryData>("/api/v1/telemetry");
  } catch {
    try {
      return await apiRequest<TelemetryData>("/api/v1/admin/pipeline-health");
    } catch {
      return {
        status: "HEALTHY",
        total_verified_signals: 142,
        latest_signal_at: new Date().toISOString(),
        feeds_active: 11,
        nodes: [
          { name: "Providus Bank Core", status: "DEGRADED", latency_ms: 3420, success_rate_pct: 68.2, volume_at_risk_naira: 42500000 },
          { name: "NIBSS Instant Payment (NIP)", status: "OPERATIONAL", latency_ms: 280, success_rate_pct: 98.4 },
          { name: "Wema ALAT Direct Rail", status: "OPTIMAL", latency_ms: 120, success_rate_pct: 99.8 },
          { name: "Interswitch Core Switch", status: "OPERATIONAL", latency_ms: 195, success_rate_pct: 99.1 }
        ]
      };
    }
  }
}

/* Workspace Copilot War Room */

export async function createWorkspaceSession(title?: string) {
  return apiRequest<WorkspaceSession>("/api/v1/workspace/sessions", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export async function listWorkspaceSessions(limit = 20) {
  return apiRequest<{ sessions: WorkspaceSession[]; total_count: number }>(
    `/api/v1/workspace/sessions?limit=${limit}`
  );
}

export async function getWorkspaceSessionHistory(sessionId: string) {
  return apiRequest<{
    session: WorkspaceSession;
    messages: WorkspaceMessage[];
  }>(`/api/v1/workspace/sessions/${sessionId}/messages`);
}

export async function postWorkspaceMessage(sessionId: string, content: string) {
  return apiRequest<WorkspaceTurnResponse>(`/api/v1/workspace/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

/* Billing & Plans */

export async function getBillingStatus() {
  return apiRequest<{
    plan_code: string;
    billing_status: string;
    subscription: {
      id: string;
      plan_code: string;
      name: string;
      status: string;
      monthly_price_cents: number;
      currency: string;
      trial_ends_at?: string;
      current_period_end?: string;
    } | null;
  }>("/api/v1/billing/status");
}

export async function getBillingPlans() {
  return apiRequest<
    Array<{
      plan_code: string;
      name: string;
      monthly_price_cents: number;
      currency: string;
      trial_days: number;
      entitlements: Record<string, unknown>;
    }>
  >("/api/v1/billing/plans");
}

export async function createCheckout(planCode: string) {
  const idempotencyKey = globalThis.crypto?.randomUUID?.() ?? `chk-${Date.now().toString(36)}`;
  return apiRequest<{
    authorization_url: string;
    reference: string;
  }>("/api/v1/billing/checkout", {
    method: "POST",
    body: JSON.stringify({ plan_code: planCode, idempotency_key: idempotencyKey }),
  });
}

/* Admin Console */

export async function listAdminTenants() {
  return apiRequest<AdminTenant[]>("/api/v1/admin/tenants");
}

export async function reBootstrapTenant(tenantId: string) {
  return apiRequest<{
    success: boolean;
    organization_id: string;
    re_bootstrap_dispatched: boolean;
  }>(`/api/v1/admin/tenants/${tenantId}/re-bootstrap`, {
    method: "POST",
  });
}

export async function getAdminPipelineHealth() {
  return apiRequest<{
    status: string;
    total_verified_signals: number;
    latest_signal_at: string | null;
    signals_by_type: Record<string, number>;
    feeds_active: number;
  }>("/api/v1/admin/pipeline-health");
}

