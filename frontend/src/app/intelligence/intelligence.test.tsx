import { describe, expect, it, vi } from "vitest";
import { INTELLIGENCE_TABS } from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/intelligence",
}));

describe("Intelligence Surface - 9 Canonical Domain Tabs Contract", () => {
  it("defines the exact 9 authoritative domain tabs specified in GOAL.md and Track 10", () => {
    const expectedKeys = [
      "FOR_YOU",
      "REGULATORY",
      "COMPETITION",
      "INFRASTRUCTURE",
      "MARKET_CUSTOMERS",
      "FINANCIAL_ECONOMIC",
      "CAPITAL_PARTNERSHIPS",
      "EXPANSION",
      "RISK_TRUST",
    ];

    const actualKeys = INTELLIGENCE_TABS.map((t) => t.key);
    expect(actualKeys).toEqual(expectedKeys);
  });

  it("provides comprehensive executive descriptions and operator focus for each stream", () => {
    for (const tab of INTELLIGENCE_TABS) {
      expect(tab.label.length).toBeGreaterThan(0);
      expect(tab.description.length).toBeGreaterThan(20);
      expect(tab.operatorFocus.length).toBeGreaterThan(20);
      expect(tab.icon.length).toBeGreaterThan(0);
    }
  });

  it("maps regulatory stream specifically to CBN and Nigerian statutory policy", () => {
    const regTab = INTELLIGENCE_TABS.find((t) => t.key === "REGULATORY");
    expect(regTab).toBeDefined();
    expect(regTab?.description).toContain("Central Bank of Nigeria (CBN)");
    expect(regTab?.operatorFocus).toContain("Licensing exposure");
  });

  it("maps infrastructure stream specifically to payment rails and switch uptime", () => {
    const infraTab = INTELLIGENCE_TABS.find((t) => t.key === "INFRASTRUCTURE");
    expect(infraTab).toBeDefined();
    expect(infraTab?.description).toContain("NIBSS switches");
    expect(infraTab?.operatorFocus).toContain("Dispute rates");
  });

  it("maps financial & economic stream to MPR, FX volatility, and unit economics", () => {
    const finTab = INTELLIGENCE_TABS.find((t) => t.key === "FINANCIAL_ECONOMIC");
    expect(finTab).toBeDefined();
    expect(finTab?.description).toContain("Monetary policy rate (MPR)");
    expect(finTab?.operatorFocus).toContain("Unit economics");
  });
});
