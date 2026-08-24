import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, accessToken, apiRequest, clearSession, login, logout } from "./api";
import { legalCopy } from "./legal-copy";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("apiRequest", () => {
  it("sends authenticated JSON requests with caller headers", async () => {
    const getItem = vi.fn(() => "session-token");
    vi.stubGlobal("window", { sessionStorage: { getItem } });
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ saved: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      apiRequest<{ saved: boolean }>("/context/company", {
        method: "PUT",
        body: JSON.stringify({ market: "NG" }),
        headers: { "X-Request-ID": "request-1" }
      })
    ).resolves.toEqual({ saved: true });

    expect(getItem).toHaveBeenCalledWith("sc_access_token");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/context/company",
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

  it("stores login state and exposes the browser access token", async () => {
    const sessionStorage = {
      getItem: vi.fn(() => "fresh-token"),
      setItem: vi.fn(),
      removeItem: vi.fn()
    };
    vi.stubGlobal("window", { sessionStorage });
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
      login({ workspace_id: crypto.randomUUID(), email: "pilot@example.com", password: "secret" })
    ).resolves.toMatchObject({ access_token: "fresh-token" });
    expect(sessionStorage.setItem).toHaveBeenCalledWith("sc_access_token", "fresh-token");
    expect(sessionStorage.setItem).toHaveBeenCalledWith(
      "sc_user",
      JSON.stringify({ display_name: "Pilot User" })
    );
    expect(accessToken()).toBe("fresh-token");
  });

  it("refreshes once after an authenticated 401 and retries the request", async () => {
    const sessionStorage = {
      getItem: vi.fn(() => "expired-token"),
      setItem: vi.fn(),
      removeItem: vi.fn()
    };
    vi.stubGlobal("window", { sessionStorage });
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
    expect(sessionStorage.setItem).toHaveBeenCalledWith("sc_access_token", "renewed-token");
  });

  it("clears session state when refresh or logout fails", async () => {
    const sessionStorage = {
      getItem: vi.fn(() => "expired-token"),
      setItem: vi.fn(),
      removeItem: vi.fn()
    };
    vi.stubGlobal("window", { sessionStorage });
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
    expect(sessionStorage.removeItem).toHaveBeenCalledWith("sc_access_token");
    expect(sessionStorage.removeItem).toHaveBeenCalledWith("sc_user");
  });

  it("returns no session token during server rendering", () => {
    vi.stubGlobal("window", undefined);
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
