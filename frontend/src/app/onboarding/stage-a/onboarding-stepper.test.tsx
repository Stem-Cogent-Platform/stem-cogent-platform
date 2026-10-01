import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import StageAOnboardingPage from "./page";

describe("StageAOnboardingPage (Flux Stepper Architecture)", () => {
  it("renders the 1440px Flux header with Stem Cogent mark, Restart, and Leave", () => {
    const markup = renderToStaticMarkup(<StageAOnboardingPage />);

    expect(markup).toContain("Stem Cogent");
    expect(markup).toContain("Create workspace");
    expect(markup).toContain("Restart");
    expect(markup).toContain("Leave");
    expect(markup).toContain("Reset onboarding form");
    expect(markup).toContain("Leave onboarding");
  });

  it("renders the 4-step linear navigation in the left sidebar", () => {
    const markup = renderToStaticMarkup(<StageAOnboardingPage />);

    // Step 1: Company Context
    expect(markup).toContain("Company Context");
    expect(markup).toContain("Basic organizational profile");

    // Step 2: Operating Licenses
    expect(markup).toContain("Operating Licenses");
    expect(markup).toContain("Regulatory authorizations");

    // Step 3: Settlement Rails
    expect(markup).toContain("Settlement Rails");
    expect(markup).toContain("Partner clearing &amp; banks");

    // Step 4: Product Verticals
    expect(markup).toContain("Product Verticals");
    expect(markup).toContain("Commercial product modules");
  });

  it("renders Step 1 (Company Details) fields with proper defaults and labels", () => {
    const markup = renderToStaticMarkup(<StageAOnboardingPage />);

    expect(markup).toContain("Company Details");
    expect(markup).toContain("This information defines your workspace and can be updated later.");
    expect(markup).toContain("Company / Legal Entity Name");
    expect(markup).toContain('id="companyName"');
    expect(markup).toContain('placeholder="e.g. Apex Pay Global"');

    expect(markup).toContain("Company Size");
    expect(markup).toContain('id="companySize"');
    expect(markup).toContain("11-50");

    expect(markup).toContain("Primary Operating Jurisdiction");
    expect(markup).toContain('id="jurisdiction"');
    expect(markup).toContain("Nigeria");
    expect(markup).toContain("Ghana");
    expect(markup).toContain("Kenya");
    expect(markup).toContain("Pan-African");

    expect(markup).toContain("Company Website");
    expect(markup).toContain('id="companyWebsite"');
    expect(markup).toContain('placeholder="e.g. apexpay.io"');

    expect(markup).toContain("Continue");
  });

  it("does not render obsolete dark transition screen or cluttered jurisdiction context metrics", () => {
    const markup = renderToStaticMarkup(<StageAOnboardingPage />);

    // Obsolete screens purged
    expect(markup).not.toContain("Synthesizing Footprint Intelligence");
    expect(markup).not.toContain("Bootstrapping real-time decision radar");
    expect(markup).not.toContain("Pipeline Active");
    expect(markup).not.toContain("Jurisdiction Context");
    expect(markup).not.toContain("Declare Your Operational Footprint");
    expect(markup).not.toContain("Real-time Footprint Metrics");
    expect(markup).not.toContain("4,131+");
  });

  it("conforms to the 1440px viewport specifications and design tokens", () => {
    const markup = renderToStaticMarkup(<StageAOnboardingPage />);

    // Check 1440px max-w-7xl canvas container
    expect(markup).toContain("max-w-7xl");
    // Check clean white canvas
    expect(markup).toContain("bg-white");
    // Check Cobalt Blue (#2A4BFF) button class or hover token
    expect(markup).toContain("bg-[#2A4BFF]");
  });

  it("packages stage-a payload correctly matching specification schema", () => {
    const payload = {
      company_name: "Apex Pay Global",
      jurisdiction: "Nigeria",
      company_size: "11-50",
      operating_licenses: ["PSSP", "IMTO", "CUSTOM: SEC Digital Asset VASP"],
      clearing_rails: ["NIBSS", "PROVIDUS", "CUSTOM: Kora RMB Rail"],
      active_products: ["virtual_accounts", "cross_border_fx"],
    };

    expect(payload.company_name).toBe("Apex Pay Global");
    expect(payload.jurisdiction).toBe("Nigeria");
    expect(payload.company_size).toBe("11-50");
    expect(payload.operating_licenses).toEqual([
      "PSSP",
      "IMTO",
      "CUSTOM: SEC Digital Asset VASP",
    ]);
    expect(payload.clearing_rails).toEqual([
      "NIBSS",
      "PROVIDUS",
      "CUSTOM: Kora RMB Rail",
    ]);
    expect(payload.active_products).toEqual([
      "virtual_accounts",
      "cross_border_fx",
    ]);
  });
});
