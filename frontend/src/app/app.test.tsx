import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import RootLayout, { metadata } from "./layout";
import HomePage from "./page";

describe("HomePage", () => {
  it("renders the Stem Cogent loading state", () => {
    const markup = renderToStaticMarkup(<HomePage />);

    expect(markup).toContain("Stem Cogent");
    expect(markup).toContain("Loading");
  });
});

describe("RootLayout", () => {
  it("defines the platform metadata", () => {
    expect(metadata.title).toBe("Stem Cogent");
    expect(metadata.description).toBe("Stem Cogent Decision Intelligence Platform");
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
