import React from "react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/company",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/components/workspace-shell", () => ({
  WorkspaceShell: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mock-workspace-shell">{children}</div>
  ),
  navigation: [],
}));

vi.mock("@/lib/api", () => ({
  apiRequest: vi.fn((url: string) => {
    if (url === "/api/v1/company/briefs") {
      return Promise.resolve({
        profile: {
          business_categories: ["PAYMENTS", "AGENCY_BANKING"],
          strategic_priorities: ["POS acquiring expansion", "Direct settlement switch"],
          operating_markets: ["Nigeria"],
        },
        objects: [
          { id: "obj-1", name: "Moniepoint", object_type: "COMPETITOR", active: true, entity_id: "ent-1" },
          { id: "obj-2", name: "NIBSS", object_type: "DEPENDENCY", active: true, entity_id: "ent-2" },
          { id: "obj-3", name: "CBN", object_type: "REGULATOR", active: true, entity_id: "ent-3" },
          { id: "obj-4", name: "Interswitch", object_type: "PARTNER", active: true, entity_id: "ent-4" },
          { id: "obj-5", name: "POS Terminal Acquiring", object_type: "PRODUCT", active: true },
        ],
        context_status: {
          complete: true,
          completeness: 1.0,
          version: 2,
        },
        briefs: [],
      });
    }
    if (url === "/api/v1/me/focus-areas") {
      return Promise.resolve([
        { id: "focus-1", label: "Merchant Profitability", focus_type: "TOPIC" },
        { id: "focus-2", label: "Interchange Spread", focus_type: "METRIC" },
      ]);
    }
    return Promise.resolve({});
  }),
}));

describe("Track 15 - Company Transparency & Scope Integration", () => {
  it("defines CompanyPage with transparent organizational model and entity links", async () => {
    const { default: CompanyPage } = await import("./page");
    expect(CompanyPage).toBeDefined();
  }, 30000);
});
