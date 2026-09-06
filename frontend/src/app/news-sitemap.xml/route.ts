import { SITE_BASE_URL } from "../../lib/config";
import { getPublicationIndex, plainText } from "../../lib/news";

export const revalidate = 300;

function xml(value: string) {
  return value.replace(/&(?!(amp|lt|gt|quot|apos);)/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
}

export async function GET() {
  const base = SITE_BASE_URL || "http://localhost:3000";
  const cutoff = Date.now() - 48 * 60 * 60 * 1000;
  const articles = (await getPublicationIndex(1000)).filter((article) => {
    const published = article.published_at || article.created_at;
    return new Date(published).getTime() >= cutoff;
  });
  const urls = articles.map((article) => {
    const published = article.published_at || article.created_at;
    return `<url><loc>${xml(`${base}${article.article_type === "LIVE" ? "/live" : "/articles"}/${article.slug}`)}</loc><news:news><news:publication><news:name>The Republic Bulletin</news:name><news:language>en</news:language></news:publication><news:publication_date>${xml(new Date(published).toISOString())}</news:publication_date><news:title>${xml(plainText(article.title))}</news:title></news:news></url>`;
  }).join("");
  return new Response(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">${urls}</urlset>`, {
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
}
