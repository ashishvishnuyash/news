import type { MetadataRoute } from "next";
import { SITE_BASE_URL } from "../lib/config";

export default function robots(): MetadataRoute.Robots {
  const base = SITE_BASE_URL || "http://localhost:3000";
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/", "/panels/", "/profile", "/login", "/register"] },
    sitemap: [`${base}/sitemap.xml`, `${base}/news-sitemap.xml`],
    host: base,
  };
}
