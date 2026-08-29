import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, accessToken, apiRequest, beginSso, bootstrapSession, clearSession, currentUser, login, logout, register } from "./api";
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
      apiRequest<{ saved: boolean }>("/context/company", {
        method: "PUT",
        body: JSON.stringify({ market: "NG" }),
        headers: { "X-Request-ID": "request-1" }
      })
    ).resolves.toEqual({ saved: true });

    expect(fetchMock).toHaveBeenLastCalledWith(
      "/context/company",
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

    await expect(apiRequest<{ saved: boolean }>("/context/company")).resolves.toEqual({
      saved: true
    });
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/context/company",
      "/api/v1/auth/refresh",
      "/context/company"
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
