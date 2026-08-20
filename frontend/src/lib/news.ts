import { cache } from "react";
import { apiUrl, siteUrl } from "./config";
import type {
  Article,
  ArticleIndex,
  ArticleSearchResponse,
  AuthorProfile,
  Correction,
  LiveUpdate,
  SiteSettings,
} from "./types";

const DEFAULT_SETTINGS: SiteSettings = {
  site_name: "The Republic Bulletin",
  site_motto: "Independent reporting for an informed republic",
  breaking_news: "",
  breaking_active: false,
  categories: ["India", "World", "Politics", "Business", "Technology", "Science", "Culture", "Sports", "Opinion"],
  features: { comments_enabled: true, registration_open: true, maintenance_mode: false },
};

async function readJson<T>(path: string, fallback: T, revalidate = 60): Promise<T> {
  try {
    const response = await fetch(apiUrl(path), { next: { revalidate } });
    return response.ok ? response.json() : fallback;
  } catch {
    return fallback;
  }
}

export const getSiteSettings = cache(async (): Promise<SiteSettings> => {
  const settings = await readJson<Partial<SiteSettings>>("/api/settings", {}, 60);
  return {
    ...DEFAULT_SETTINGS,
    ...settings,
    features: { ...DEFAULT_SETTINGS.features, ...settings.features },
  };
});

export const getArticle = cache(async (slug: string): Promise<Article | null> => {
  return readJson<Article | null>(`/api/articles/${encodeURIComponent(slug)}?track_view=false`, null, 60);
});

export async function searchArticles(params: Record<string, string | number | boolean | undefined | null> = {}): Promise<ArticleSearchResponse> {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  });
  return readJson<ArticleSearchResponse>(
    `/api/articles/search${search.size ? `?${search}` : ""}`,
    { items: [], total: 0, limit: Number(params.limit) || 20, offset: Number(params.offset) || 0, suggestions: [] },
    60,
  );
}

export async function getPublicationIndex(limit = 1000): Promise<ArticleIndex[]> {
  return readJson<ArticleIndex[]>(`/api/articles/index?limit=${limit}`, [], 300);
}

export async function getMostRead(limit = 8): Promise<Article[]> {
  return readJson<Article[]>(`/api/articles/most-read?limit=${limit}`, [], 60);
}

export const getAuthor = cache(async (slug: string): Promise<AuthorProfile | null> => {
  return readJson<AuthorProfile | null>(`/api/authors/${encodeURIComponent(slug)}`, null, 60);
});

export async function getCorrections(): Promise<Correction[]> {
  return readJson<Correction[]>("/api/corrections", [], 60);
}

export async function getLiveUpdates(slug: string): Promise<LiveUpdate[]> {
  return readJson<LiveUpdate[]>(`/api/live/${encodeURIComponent(slug)}`, [], 15);
}

export function articleHref(article: Pick<Article, "slug" | "article_type">) {
  const slug = article.slug || "";
  return article.article_type === "LIVE" ? `/live/${slug}` : `/articles/${slug}`;
}

export function authorHref(author: Pick<Article["author"], "slug" | "username">) {
  return `/authors/${encodeURIComponent(author.slug || author.username)}`;
}

export function absoluteUrl(value?: string | null) {
  if (!value) return undefined;
  if (/^https?:\/\//i.test(value)) return value;
  return siteUrl(value.startsWith("/") ? value : `/${value}`);
}

export function plainText(value = "") {
  return value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

export function articlePreview(article: Article, length = 180) {
  const value = article.summary?.trim() || plainText(article.content);
  return value.length > length ? `${value.slice(0, length).trim()}…` : value;
}

export function readingMinutes(content = "") {
  const words = plainText(content).split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 220));
}

export function splitEditorialList(value?: string | null) {
  if (!value) return [];
  return value.split(/\r?\n|;/).map((item) => item.replace(/^[-*]\s*/, "").trim()).filter(Boolean);
}

export function formatNewsDate(value?: string | null, includeTime = false) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    ...(includeTime ? { timeStyle: "short" as const } : {}),
  }).format(new Date(value));
}
