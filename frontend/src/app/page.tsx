"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import Header from "./components/Header";
import OnboardingTour from "./components/OnboardingTour";
import { apiUrl } from "../lib/config";

interface Article {
  id: number;
  slug: string;
  title: string;
  content: string;
  summary: string;
  category: string;
  image_url?: string;
  image_caption?: string;
  tags?: string;
  view_count?: number;
  is_pinned?: boolean;
  is_breaking?: boolean;
  created_at: string;
  published_at?: string;
  author: {
    username: string;
  };
}

function formatDate(dateStr?: string) {
  if (!dateStr) return "N/A";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function stripHtml(content = "") {
  return content.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function getArticlePreview(article: Article, length = 280) {
  const source = article.summary || stripHtml(article.content);
  if (source.length <= length) return source;
  return `${source.slice(0, length).trim()}...`;
}

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [category, setCategory] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [density, setDensity] = useState("broadsheet");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchArticles = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (category !== "All") params.append("category", category);
      if (searchQuery.trim()) params.append("q", searchQuery.trim());

      const res = await fetch(apiUrl(`/api/articles${params.toString() ? `?${params}` : ""}`));
      if (!res.ok) {
        throw new Error(`Article request failed with ${res.status}`);
      }
      setArticles(await res.json());
    } catch (err) {
      console.error("Error fetching articles:", err);
      setError("Unable to reach The Republic Bulletin pressroom. Ensure backend server on port 8000 is online.");
      setArticles([]);
    } finally {
      setLoading(false);
    }
  }, [category, searchQuery]);

  useEffect(() => {
    const timer = window.setTimeout(fetchArticles, 200);
    return () => window.clearTimeout(timer);
  }, [fetchArticles]);

  const featured = useMemo(() => articles.find((a) => a.is_pinned) || articles[0], [articles]);
  const secondaryArticles = useMemo(() => articles.filter((a) => a.id !== featured?.id), [articles, featured]);

  const gridClass = useMemo(() => {
    if (density === "single") return "trb-grid-single";
    if (density === "tabloid") return "trb-grid-tabloid";
    return "trb-grid-broadsheet";
  }, [density]);

  const totalReads = useMemo(
    () => articles.reduce((sum, a) => sum + (a.view_count || 0), 0),
    [articles]
  );

  return (
    <div className="trb-container">
      {/* 1. Header Navigation */}
      <Header
        currentCategory={category}
        onCategoryChange={setCategory}
        onSearchChange={setSearchQuery}
        activeDensity={density}
        onDensityChange={setDensity}
      />

      {/* 2. Main Dispatches Section */}
      <main id="main-content" style={{ marginTop: "1.5rem" }}>
        {error && (
          <div style={{ padding: "1rem", marginBottom: "1.5rem", border: "2px solid var(--accent-red)", color: "var(--accent-red)", fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 700 }}>
            ⚠️ {error}
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: "center", padding: "6rem 1rem", fontFamily: "var(--font-mono)", fontSize: "0.85rem", letterSpacing: "2px", textTransform: "uppercase", borderTop: "3px double var(--border-color)", borderBottom: "3px double var(--border-color)" }}>
            📜 RETRIEVING BROADSIDE DISPATCHES FROM THE ARCHIVE...
          </div>
        ) : articles.length === 0 ? (
          <div style={{ textAlign: "center", padding: "5rem 2rem", border: "2px dashed var(--border-color)", margin: "2rem 0" }}>
            <h2 style={{ fontFamily: "var(--font-headline)", fontSize: "2rem", textTransform: "uppercase", marginBottom: "0.5rem" }}>No Dispatches Found</h2>
            <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", opacity: 0.8, marginBottom: "1.5rem" }}>
              There are no published stories in the public records matching your current category filter or search terms.
            </p>
            <button
              type="button"
              onClick={() => {
                setCategory("All");
                setSearchQuery("");
              }}
              className="trb-btn-solid"
            >
              Reset Archive Filters
            </button>
          </div>
        ) : (
          <div>
            {/* ─── LEAD FEATURED STORY ─── */}
            {featured && (
              <section className={`trb-lead-story ${featured.image_url ? "" : "trb-lead-story--text-only"}`} id="featured-dispatch">
                <div>
                  <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.5rem", fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--accent-red)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px", marginBottom: "0.5rem" }}>
                    {featured.is_pinned && <span className="trb-badge-red">⭐ LEAD STORY</span>}
                    {featured.is_breaking && <span className="trb-badge-red" style={{ backgroundColor: "#D32F2F" }}>⚡ BREAKING</span>}
                    <span className="trb-btn-pill" style={{ pointerEvents: "none" }}>{featured.category}</span>
                    <span>•</span>
                    <span>{formatDate(featured.published_at || featured.created_at)}</span>
                  </div>

                  <h1 className="trb-lead-title">
                    <Link href={`/articles/${featured.slug}`}>
                      {featured.title}
                    </Link>
                  </h1>

                  <p className="trb-dropcap">
                    {getArticlePreview(featured, 420)}
                  </p>

                  <div className="trb-byline-bar">
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span style={{ width: "24px", height: "24px", borderRadius: "50%", background: "var(--fg-ink)", color: "var(--bg-paper)", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: "0.7rem" }}>
                        {featured.author.username.charAt(0).toUpperCase()}
                      </span>
                      <span>DISPATCH BY {featured.author.username}</span>
                    </div>

                    <Link href={`/articles/${featured.slug}`} className="trb-btn-solid" style={{ textDecoration: "none" }}>
                      READ FULL DISPATCH →
                    </Link>
                  </div>
                </div>

                {featured.image_url && (
                  <div>
                    <Link href={`/articles/${featured.slug}`} className="trb-lead-image-box" style={{ display: "block", textDecoration: "none" }}>
                      <Image src={featured.image_url} alt={featured.title} className="trb-lead-image" width={720} height={440} priority />
                    </Link>
                    {featured.image_caption && <p className="article-image-caption">{featured.image_caption}</p>}
                  </div>
                )}
              </section>
            )}

            {/* ─── SECONDARY DISPATCHES & SIDEBAR ─── */}
            {secondaryArticles.length > 0 && (
              <div className="trb-dispatches-layout">
                {/* Dispatches Grid */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "3px double var(--border-color)", paddingBottom: "0.5rem", marginBottom: "1.5rem", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "1px" }}>
                    <h2 style={{ fontFamily: "var(--font-headline)", fontSize: "1.4rem", fontWeight: 900 }}>Recent Dispatches & Columns</h2>
                    <span className="trb-badge-red" style={{ backgroundColor: "var(--fg-ink)" }}>
                      {secondaryArticles.length} STORIES AVAILABLE
                    </span>
                  </div>

                  <div className={gridClass}>
                    {secondaryArticles.map((art) => (
                      <article key={art.id} className="trb-article-card">
                        <div>
                          {art.image_url && (
                            <Link href={`/articles/${art.slug}`} className="trb-card-media">
                              <Image src={art.image_url} alt="" width={480} height={300} />
                            </Link>
                          )}
                          {art.image_url && art.image_caption && (
                            <p className="card-image-caption">{art.image_caption}</p>
                          )}

                          <div className="trb-card-meta">
                            <span style={{ fontWeight: 700, color: "var(--accent-red)" }}>{art.category}</span>
                            <span>{formatDate(art.published_at || art.created_at)}</span>
                          </div>

                          <h3 className="trb-card-title">
                            <Link href={`/articles/${art.slug}`}>{art.title}</Link>
                          </h3>

                          <p style={{ fontSize: "0.9rem", lineHeight: 1.6, opacity: 0.9 }}>
                            {getArticlePreview(art, 160)}
                          </p>
                        </div>

                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border-color)", paddingTop: "0.6rem", marginTop: "1rem", fontFamily: "var(--font-mono)", fontSize: "0.7rem", fontWeight: 700 }}>
                          <span>BY {art.author.username.toUpperCase()}</span>
                          <Link href={`/articles/${art.slug}`} className="trb-btn-pill" style={{ textDecoration: "none" }}>
                            READ →
                          </Link>
                        </div>
                      </article>
                    ))}
                  </div>
                </div>

                {/* Sidebar */}
                <aside>
                  {/* Archives Search */}
                  <div className="trb-sidebar-card">
                    <h3 className="trb-sidebar-heading">🔎 Pressroom Archives</h3>
                    <form onSubmit={(e) => { e.preventDefault(); fetchArticles(); }} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                      <input
                        type="search"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Keywords, correspondents, tags..."
                        className="trb-input"
                        style={{ width: "100%" }}
                      />
                      <button type="submit" className="trb-btn-solid">
                        SEARCH DISPATCHES
                      </button>
                    </form>
                  </div>

                  {/* Stats */}
                  <div className="trb-sidebar-card">
                    <h3 className="trb-sidebar-heading">📊 Edition Statistics</h3>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", textAlign: "center", fontFamily: "var(--font-mono)" }}>
                      <div style={{ border: "1px solid var(--border-color)", padding: "0.75rem", borderRadius: "3px", background: "var(--bg-paper)" }}>
                        <span style={{ display: "block", fontSize: "1.6rem", fontWeight: 900 }}>{articles.length}</span>
                        <span style={{ fontSize: "0.65rem", textTransform: "uppercase", opacity: 0.8, fontWeight: 700 }}>Dispatches</span>
                      </div>
                      <div style={{ border: "1px solid var(--border-color)", padding: "0.75rem", borderRadius: "3px", background: "var(--bg-paper)" }}>
                        <span style={{ display: "block", fontSize: "1.6rem", fontWeight: 900 }}>{totalReads}</span>
                        <span style={{ fontSize: "0.65rem", textTransform: "uppercase", opacity: 0.8, fontWeight: 700 }}>Total Reads</span>
                      </div>
                    </div>
                  </div>

                  {/* Creed */}
                  <div className="trb-sidebar-card">
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", fontWeight: 700, color: "var(--accent-red)", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.4rem", marginBottom: "0.75rem" }}>
                      ⚜️ THE EDITOR&apos;S CREED
                    </div>
                    <p style={{ fontFamily: "var(--font-headline)", fontStyle: "italic", fontSize: "0.95rem", lineHeight: 1.6 }}>
                      &ldquo;We print sourced dispatches with uncompromised integrity. Read deeply, reflect patiently, and protect the public truth in black and white.&rdquo;
                    </p>
                    <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", fontWeight: 700, textAlign: "right", marginTop: "0.75rem", textTransform: "uppercase" }}>
                      — Managing Editorial Board
                    </p>
                  </div>
                </aside>
              </div>
            )}
          </div>
        )}
      </main>

      {/* 3. Footer */}
      <footer style={{ marginTop: "4rem", borderTop: "4px double var(--border-color)", paddingTop: "1.5rem", textAlign: "center", fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
        <p style={{ fontWeight: 800, letterSpacing: "1px", fontSize: "0.85rem", marginBottom: "0.4rem" }}>
          THE REPUBLIC BULLETIN PUBLISHING HOUSE
        </p>

        <p style={{ opacity: 0.75 }}>
          ALL RIGHTS RESERVED • PRINTED ON VINTAGE STACK DIGITAL PRESSES • UNIFIED SUBDOMAIN ARCHITECTURE
        </p>
      </footer>

      <OnboardingTour />
    </div>
  );
}
