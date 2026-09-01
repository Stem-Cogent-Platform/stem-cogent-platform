import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  acceptInvitation,
  accessToken,
  adminMfaLogin,
  apiRequest,
  beginSso,
  bootstrapSession,
  clearSession,
  currentUser,
  login,
  logout,
  recordProductEvent,
  register,
  validateInvitation
} from "./api";
import { legalCopy } from "./legal-copy";

afterEach(() => {
  clearSession();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("apiRequest", () => {
  it("sends authenticated JSON requests with caller headers", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "session-token", expires_in: 900, user: {} }), { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(
      new Response(JSON.stringify({ saved: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      }));
    vi.stubGlobal("fetch", fetchMock);
    await login({ email: "person@example.com", password: "twelve-characters" });

    await expect(
      apiRequest<{ saved: boolean }>("/api/v1/context/company", {
        method: "PUT",
        body: JSON.stringify({ market: "NG" }),
        headers: { "X-Request-ID": "request-1" }
      })
    ).resolves.toEqual({ saved: true });

    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/v1/context/company",
      expect.objectContaining({
        credentials: "include",
        headers: expect.objectContaining({
          Accept: "application/json",
          Authorization: "Bearer session-token",
          "Content-Type": "application/json",
          "X-Request-ID": "request-1"
        })
      })
    );
  });

  it.each([
    [{ detail: "Consent is required" }, "Consent is required", undefined],
    [{ detail: { message: "Plan is inactive", code: "BILLING_INACTIVE" } }, "Plan is inactive", "BILLING_INACTIVE"],
    [{}, "We could not complete that request. Please try again.", undefined]
  ])("normalises API errors without leaking response data", async (payload, message, code) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify(payload), {
          status: 403,
          headers: { "Content-Type": "application/json" }
        })
      )
    );

    const failure = await apiRequest("/protected").catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(ApiError);
    expect(failure).toMatchObject({ message, status: 403, code });
  });

  it("handles a non-JSON success body without client failure", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 204 })));
    await expect(apiRequest("/health")).resolves.toEqual({});
  });

  it("rejects frontend HTML returned in place of API JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("<html>frontend fallback</html>", {
        status: 200,
        headers: { "Content-Type": "text/html" }
      }))
    );

    await expect(apiRequest("/api/v1/briefs")).rejects.toMatchObject({
      status: 200,
      code: "INVALID_API_RESPONSE"
    });
  });

  it("turns browser transport failures into an actionable API error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));

    await expect(apiRequest("/api/v1/briefs")).rejects.toMatchObject({
      status: 0,
      code: "NETWORK_UNAVAILABLE",
      message: "Stem could not reach the intelligence service. Check your connection and try again."
    });
  });

  it("keeps login state in memory instead of browser storage", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            access_token: "fresh-token",
            expires_in: 900,
            user: { display_name: "Pilot User" }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
    );

    await expect(
      login({ email: "pilot@example.com", password: "correct-password" })
    ).resolves.toMatchObject({ access_token: "fresh-token" });
    expect(accessToken()).toBe("fresh-token");
    expect(currentUser()).toEqual({ display_name: "Pilot User" });
  });

  it("creates public trial sessions and begins provider sign-in through the API", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "trial-token", expires_in: 900, user: { workspace_name: "Acme" } }), { status: 201, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ authorization_url: "https://accounts.google.com/authorize" }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    await register({ company_name: "Acme", display_name: "Ada User", email: "ada@example.com", password: "long-secure-password" });
    await expect(beginSso("google", "signup")).resolves.toEqual({ authorization_url: "https://accounts.google.com/authorize" });

    expect(accessToken()).toBe("trial-token");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/auth/register");
    expect(fetchMock.mock.calls[1][0]).toBe("http://localhost:8000/api/v1/auth/sso/google/start?intent=signup");
  });

  it("validates and accepts a tenant invitation", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ valid: true, workspace_name: "Acme", email: "invitee@example.com", expires_at: "2026-09-01T00:00:00Z" }), { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "invited-token", expires_in: 900, user: { display_name: "Invitee" } }), { status: 201, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(validateInvitation("token with spaces")).resolves.toMatchObject({ valid: true, workspace_name: "Acme" });
    await expect(acceptInvitation({ token: "token", display_name: "Invitee", password: "long-secure-password" })).resolves.toMatchObject({ access_token: "invited-token" });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/auth/invitations/validate?token=token%20with%20spaces");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/auth/invitations/accept");
    expect(accessToken()).toBe("invited-token");
  });

  it("creates an MFA-verified internal operator session", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ access_token: "operator-token", expires_in: 900, user: { permission_role: "SYSTEM_ADMIN" } }), { status: 200, headers: { "Content-Type": "application/json" } })
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(adminMfaLogin({ email: "operator@example.com", password: "long-secure-password", totp_code: "123456" })).resolves.toMatchObject({ access_token: "operator-token" });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/admin/mfa", expect.objectContaining({ method: "POST" }));
    expect(currentUser()).toMatchObject({ permission_role: "SYSTEM_ADMIN" });
  });

  it("records analytics without blocking the primary action when delivery fails", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "session-token", expires_in: 900, user: {} }), { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);
    await login({ email: "pilot@example.com", password: "correct-password" });

    await expect(recordProductEvent("BRIEFING_VIEWED", { object_type: "BRIEF", object_id: "brief-1", metadata: { source: "home" } })).resolves.toBeUndefined();
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/events");
  });

  it("refreshes once after an authenticated 401 and retries the request", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ access_token: "expired-token", expires_in: 900, user: {} }), { status: 200, headers: { "Content-Type": "application/json" } })));
    await login({ email: "pilot@example.com", password: "correct-password" });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Expired" }), {
          status: 401,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ access_token: "renewed-token", expires_in: 900, user: {} }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest<{ ok: boolean }>("/protected")).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(accessToken()).toBe("renewed-token");
  });

  it("restores a cookie-backed session after an in-memory page reload", async () => {
    clearSession();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Bearer token required" }), {
          status: 401,
          headers: { "Content-Type": "application/json" }
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "restored-token",
            expires_in: 900,
            user: { display_name: "Reloaded User" }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ saved: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest<{ saved: boolean }>("/api/v1/context/company")).resolves.toEqual({
      saved: true
    });
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/context/company",
      "/api/v1/auth/refresh",
      "/api/v1/context/company"
    ]);
    expect(accessToken()).toBe("restored-token");
  });

  it("restores an SSO session from the API host when the same-origin cookie is absent", async () => {
    clearSession();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "No refresh session" }), { status: 401, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "sso-token", expires_in: 900, user: { display_name: "SSO User" } }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(bootstrapSession()).resolves.toBe(true);
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/auth/refresh",
      "http://localhost:8000/api/v1/auth/refresh"
    ]);
    expect(accessToken()).toBe("sso-token");
  });

  it("clears session state when refresh or logout fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ access_token: "expired-token", expires_in: 900, user: {} }), { status: 200, headers: { "Content-Type": "application/json" } })));
    await login({ email: "pilot@example.com", password: "correct-password" });
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ detail: "Unavailable" }), {
        status: 401,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest("/protected")).rejects.toMatchObject({ status: 401 });
    await expect(logout()).rejects.toMatchObject({ status: 401 });
    clearSession();
    expect(accessToken()).toBeNull();
    expect(currentUser()).toBeNull();
  });

  it("returns no token after an explicit session clear", () => {
    clearSession();
    expect(accessToken()).toBeNull();
    expect(() => clearSession()).not.toThrow();
  });
});

describe("published legal copy", () => {
  it("is versioned and names the governing Nigerian data protection law", () => {
    expect(legalCopy.terms.version).toBe("2026-08-24");
    expect(legalCopy.privacy.version).toBe("2026-08-24");
    expect(legalCopy.privacy.sections.flat().join(" ")).toContain("Nigeria Data Protection Act 2023");
    expect(legalCopy.privacy.sections.flat().join(" ")).toContain("Nigeria Data Protection Commission");
  });
});
