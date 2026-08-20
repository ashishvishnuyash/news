import type { Metadata } from "next";
import Link from "next/link";
import ArticleCard from "../components/ArticleCard";
import PageHeader from "../components/PageHeader";
import PublicShell from "../components/PublicShell";
import AnalyticsEvent from "../components/AnalyticsEvent";
import { getSiteSettings, searchArticles } from "../../lib/news";

export const metadata: Metadata = { title: "Search", description: "Search The Republic Bulletin reporting archive." };

type SearchProps = { searchParams: Promise<Record<string, string | string[] | undefined>> };

function value(params: Record<string, string | string[] | undefined>, key: string) {
  const item = params[key];
  return Array.isArray(item) ? item[0] || "" : item || "";
}

function pageHref(params: URLSearchParams, page: number) {
  const next = new URLSearchParams(params);
  next.set("page", String(page));
  return `/search?${next}`;
}

export default async function SearchPage({ searchParams }: SearchProps) {
  const raw = await searchParams;
  const q = value(raw, "q");
  const category = value(raw, "category");
  const author = value(raw, "author");
  const dateFrom = value(raw, "date_from");
  const dateTo = value(raw, "date_to");
  const sort = value(raw, "sort") || (q ? "relevance" : "newest");
  const page = Math.max(1, Number(value(raw, "page")) || 1);
  const limit = 20;
  const [result, settings] = await Promise.all([
    searchArticles({
      q,
      category,
      author,
      date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
      date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
      sort,
      limit,
      offset: (page - 1) * limit,
    }),
    getSiteSettings(),
  ]);
  const totalPages = Math.max(1, Math.ceil(result.total / limit));
  const currentQuery = new URLSearchParams();
  [["q", q], ["category", category], ["author", author], ["date_from", dateFrom], ["date_to", dateTo], ["sort", sort]].forEach(([key, entry]) => { if (entry) currentQuery.set(key, entry); });

  return (
    <PublicShell>
      <AnalyticsEvent name="search" properties={{ has_query: Boolean(q), category: category || "all", author_filter: Boolean(author), date_filter: Boolean(dateFrom || dateTo), sort, result_count: result.total }} />
      <PageHeader eyebrow="Archive desk" title="Search the reporting archive" description="Search published reporting by keyword, section, author, date, or reader interest." crumbs={[{ label: "Search" }]} />
      <form className="advanced-search" action="/search" method="get" role="search">
        <label className="search-wide">Keywords<input type="search" name="q" defaultValue={q} placeholder="Headline, topic, source, or phrase" /></label>
        <label>Section<select name="category" defaultValue={category}><option value="">All sections</option>{settings.categories.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label>Author<input name="author" defaultValue={author} placeholder="Username or author slug" /></label>
        <label>From<input type="date" name="date_from" defaultValue={dateFrom} /></label>
        <label>To<input type="date" name="date_to" defaultValue={dateTo} /></label>
        <label>Sort<select name="sort" defaultValue={sort}><option value="relevance">Relevance</option><option value="newest">Newest</option><option value="oldest">Oldest</option><option value="most_read">Most read</option></select></label>
        <button className="trb-btn-solid">Search</button>
      </form>

      <div className="search-summary"><strong>{result.total}</strong> {result.total === 1 ? "story" : "stories"} found{q ? ` for “${q}”` : ""}</div>
      {result.suggestions.length > 0 && <div className="search-suggestions"><span>Top matches:</span>{result.suggestions.map((title) => <span key={title}>{title}</span>)}</div>}
      {result.items.length === 0 ? (
        <section className="public-empty-state"><h2>No matching stories</h2><p>Try fewer keywords, remove a filter, or browse the full archive.</p><Link href="/archive" className="trb-btn-solid">Browse archive</Link></section>
      ) : (
        <div className="search-results">{result.items.map((article) => <ArticleCard key={article.id} article={article} />)}</div>
      )}
      {totalPages > 1 && <nav className="pagination" aria-label="Search result pages"><Link aria-disabled={page <= 1} href={pageHref(currentQuery, Math.max(1, page - 1))}>Previous</Link><span>Page {page} of {totalPages}</span><Link aria-disabled={page >= totalPages} href={pageHref(currentQuery, Math.min(totalPages, page + 1))}>Next</Link></nav>}
    </PublicShell>
  );
}
