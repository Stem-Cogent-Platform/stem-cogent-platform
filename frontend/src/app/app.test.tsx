import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() })
}));

import RootLayout, { metadata } from "./layout";
import HomePage from "./page";

describe("HomePage", () => {
  it("renders the locked legal-consent onboarding checkpoint", () => {
    const markup = renderToStaticMarkup(<HomePage />);

    expect(markup).toContain("Secure workspace setup");
    expect(markup).toContain("Legal consent");
    expect(markup).toContain("Preparing the current documents");
    expect(markup).not.toContain("Company Context is now available");
  });
});

describe("RootLayout", () => {
  it("defines the platform metadata", () => {
    expect(metadata.title).toEqual({
      default: "Stem Cogent | Decision Intelligence for Nigerian Fintech",
      template: "%s · Stem Cogent"
    });
    expect(metadata.description).toContain("Evidence-backed decision intelligence");
    expect(metadata.alternates).toEqual({ canonical: "/" });
  });

  it("renders an English document with its children", () => {
    const markup = renderToStaticMarkup(
      <RootLayout>
        <main>Dashboard</main>
      </RootLayout>
    );

    expect(markup).toContain('<html lang="en">');
    expect(markup).toContain("<main>Dashboard</main>");
  });
});

describe("Visual token contract", () => {
  it("uses the approved light-first Stem system without forbidden effects", () => {
    const css = readFileSync(resolve(process.cwd(), "src/app/globals.css"), "utf8");
    const source = readFileSync(resolve(process.cwd(), "src/app/page.tsx"), "utf8");

    expect(css).toContain("--bg-page: #f5f6fa");
    expect(css).toContain("--accent: #2a4bff");
    expect(css).toContain("--text-primary: #0b0f1a");
    expect(`${css}\n${source}`).not.toMatch(/linear-gradient|radial-gradient|dark:|neon|text-shadow|filter:\s*drop-shadow/i);
  });
});
