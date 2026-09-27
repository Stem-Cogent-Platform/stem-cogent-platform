import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { DynamicTagPicker } from "./DynamicTagPicker";

describe("DynamicTagPicker Component", () => {
  const standardOptions = [
    { id: "PSSP", label: "PSSP", desc: "Payment Solutions Service Provider" },
    { id: "MMO", label: "MMO", desc: "Mobile Money Operator" },
    { id: "Switching", label: "Switching", desc: "Switching & Processing" },
  ];

  it("renders standard pre-configured tag options with clean resting and active states", () => {
    const markup = renderToStaticMarkup(
      <DynamicTagPicker
        standardOptions={standardOptions}
        selected={["PSSP"]}
        onChange={vi.fn()}
        label="Operating Licenses"
      />
    );

    expect(markup).toContain("Operating Licenses");
    expect(markup).toContain("PSSP");
    expect(markup).toContain("MMO");
    expect(markup).toContain("Switching");
    expect(markup).toContain("Add Custom");
    expect(markup).toContain('aria-pressed="true"');
  });

  it("renders pre-existing custom tags with Custom badge and remove button", () => {
    const markup = renderToStaticMarkup(
      <DynamicTagPicker
        standardOptions={standardOptions}
        selected={["PSSP", "SEC Digital Asset VASP", "Kora RMB Rail"]}
        onChange={vi.fn()}
      />
    );

    expect(markup).toContain("SEC Digital Asset VASP");
    expect(markup).toContain("Kora RMB Rail");
    expect(markup).toContain("Custom");
    expect(markup).toContain('aria-label="Remove custom tag SEC Digital Asset VASP"');
    expect(markup).toContain('aria-label="Remove custom tag Kora RMB Rail"');
  });

  it("submits custom license and rail tags cleanly in payload structure", () => {
    const payload = {
      company_name: "Apex Pay Global Ltd",
      operating_licenses: ["PSSP", "SEC Digital Asset VASP"],
      clearing_rails: ["NIBSS", "Kora RMB Rail"],
      active_products: ["Virtual Accounts"],
      primary_country: "NG",
    };

    expect(payload.operating_licenses).toContain("SEC Digital Asset VASP");
    expect(payload.clearing_rails).toContain("Kora RMB Rail");
    expect(JSON.stringify(payload)).toContain('"operating_licenses":["PSSP","SEC Digital Asset VASP"]');
    expect(JSON.stringify(payload)).toContain('"clearing_rails":["NIBSS","Kora RMB Rail"]');
  });
});
