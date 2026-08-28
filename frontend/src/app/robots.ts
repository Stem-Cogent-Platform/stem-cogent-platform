import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/login", "/legal/privacy", "/legal/terms"],
      disallow: [
        "/alerts",
        "/billing",
        "/briefing",
        "/briefs",
        "/company",
        "/digests",
        "/entities",
        "/intelligence",
        "/onboarding",
        "/pilot",
        "/settings",
        "/watchlist"
      ]
    },
    sitemap: "https://stem-cogent.com/sitemap.xml",
    host: "https://stem-cogent.com"
  };
}
