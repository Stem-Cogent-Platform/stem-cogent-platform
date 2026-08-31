import { describe, expect, it } from "vitest";

import robots from "./robots";
import sitemap from "./sitemap";

describe("public search discovery", () => {
  it("publishes the canonical sitemap while excluding private workspace routes", () => {
    const policy = robots();

    expect(policy.sitemap).toBe("https://stem-cogent.com/sitemap.xml");
    expect(policy.host).toBe("https://stem-cogent.com");
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
      "https://stem-cogent.com",
      "https://stem-cogent.com/login",
      "https://stem-cogent.com/legal/privacy",
      "https://stem-cogent.com/legal/terms"
    ]);
  });
});
