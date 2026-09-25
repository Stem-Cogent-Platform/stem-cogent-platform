import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/company",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/components/workspace-shell", async () => {
  const actual = await vi.importActual<typeof import("@/components/workspace-shell")>(
    "@/components/workspace-shell"
  );
  return {
    ...actual,
    WorkspaceShell: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="mock-workspace-shell">{children}</div>
    ),
  };
});

import WatchlistPage from "./page";
import { navigation } from "@/components/workspace-shell";

describe("Track 11 - Remove Watchlist from primary customer product", () => {
  it("renders educational notice that monitoring scope is automated via Company Context + Focus Areas", () => {
    const markup = renderToStaticMarkup(<WatchlistPage />);

    expect(markup).toContain("Watchlist Is Now Automated");
    expect(markup).toContain("Company Context + Focus Areas = Monitoring Scope");
    expect(markup).toContain("Go to Company Scope →");
    expect(markup).toContain('href="/company"');
  });

  it("does not render a standalone manual watchlist table or form", () => {
    const markup = renderToStaticMarkup(<WatchlistPage />);

    expect(markup).not.toContain("Add a Focus Area");
    expect(markup).not.toContain("watchlist-tabs");
  });

  it("ensures primary navigation in WorkspaceShell adheres to Track 16 navigation cleanup", () => {
    // 1. Verify /watchlist, /alerts, and /digests are absent from primary nav
    const navItems = navigation as readonly (readonly [string, string, string])[];
    expect(navItems.some(([href]) => href === "/watchlist")).toBe(false);
    expect(navItems.some(([href]) => href === "/alerts")).toBe(false);
    expect(navItems.some(([href]) => href === "/digests")).toBe(false);

    // 2. Verify exact canonical primary destinations
    expect(navigation.map(([href]) => href)).toEqual([
      "/radar",
      "/artifacts",
      "/workspace",
      "/settings",
    ]);

    // 3. Verify labels
    expect(navigation.map(([, label]) => label)).toEqual([
      "Radar Feed",
      "Decision Artifacts",
      "Executive Copilot",
      "Company & Settings",
    ]);
  });
});
