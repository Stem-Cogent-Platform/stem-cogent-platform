import { describe, expect, it } from "vitest";

import robots from "./robots";
import sitemap from "./sitemap";

describe("public search discovery", () => {
  it("publishes the canonical sitemap while excluding private workspace routes", () => {
    const policy = robots();

    expect(policy.sitemap).toBe("https://app.stem-cogent.com/sitemap.xml");
    expect(policy.host).toBe("https://app.stem-cogent.com");
    expect(policy.rules).toMatchObject({
      allow: ["/", "/login", "/legal/privacy", "/legal/terms"]
    });
    expect(policy.rules).toMatchObject({
      disallow: expect.arrayContaining(["/briefs", "/company", "/settings"])
    });
  });

  it("lists only public pages under the canonical application origin", () => {
    const entries = sitemap();

    expect(entries.map((entry) => entry.url)).toEqual([
      "https://app.stem-cogent.com",
      "https://app.stem-cogent.com/login",
      "https://app.stem-cogent.com/legal/privacy",
      "https://app.stem-cogent.com/legal/terms"
    ]);
  });
});
