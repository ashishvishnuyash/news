import type { MetadataRoute } from "next";
import { SITE_BASE_URL } from "../lib/config";
import { absoluteUrl, getPublicationIndex } from "../lib/news";

const STATIC_ROUTES = ["", "/search", "/archive", "/breaking", "/fact-check", "/about", "/editorial-standards", "/corrections", "/contact", "/privacy", "/terms", "/copyright", "/advertising"];

function xmlEscape(value: string): string {
  return value
    .replace(/&(?!(amp|lt|gt|quot|apos);)/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = SITE_BASE_URL || "http://localhost:3000";
  const articles = await getPublicationIndex(5000);
  const staticEntries: MetadataRoute.Sitemap = STATIC_ROUTES.map((path) => ({
    url: xmlEscape(`${base}${path || "/"}`),
    changeFrequency: path === "" ? "hourly" : "weekly",
    priority: path === "" ? 1 : 0.65,
  }));
  const articleEntries: MetadataRoute.Sitemap = articles.map((article) => {
    const rawImage = article.image_url ? absoluteUrl(article.image_url) : undefined;
    return {
      url: xmlEscape(`${base}${article.article_type === "LIVE" ? "/live" : "/articles"}/${article.slug}`),
      lastModified: article.updated_at,
      changeFrequency: article.article_type === "LIVE" ? "always" : "weekly",
      priority: 0.85,
      ...(rawImage ? { images: [xmlEscape(rawImage)] } : {}),
    };
  });
  const authorEntries: MetadataRoute.Sitemap = [...new Map(articles.map((article) => [article.author.id, article.author])).values()].map((author) => ({
    url: xmlEscape(`${base}/authors/${encodeURIComponent(author.slug || author.username)}`),
    changeFrequency: "weekly",
    priority: 0.6,
  }));
  const sectionEntries: MetadataRoute.Sitemap = [...new Set(articles.map((article) => article.category))].map((category) => ({
    url: xmlEscape(`${base}/section/${encodeURIComponent(category.toLowerCase())}`),
    changeFrequency: "daily" as const,
    priority: 0.7,
  }));
  return [...staticEntries, ...articleEntries, ...authorEntries, ...sectionEntries];
}

