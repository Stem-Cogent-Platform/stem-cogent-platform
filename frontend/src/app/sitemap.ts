import type { MetadataRoute } from "next";

const PUBLIC_ROUTES = ["", "/login", "/legal/privacy", "/legal/terms"] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_ROUTES.map((path, index) => ({
    url: `https://stem-cogent.com${path}`,
    changeFrequency: index === 0 ? "weekly" : "monthly",
    priority: index === 0 ? 1 : 0.5
  }));
}
