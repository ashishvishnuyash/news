import type { Metadata } from "next";
import Link from "next/link";
import PageHeader from "../components/PageHeader";
import PublicShell from "../components/PublicShell";
import { articleHref, formatNewsDate, getPublicationIndex } from "../../lib/news";

export const metadata: Metadata = { title: "News Archive", description: "Browse The Republic Bulletin archive by year, month, and section." };

type ArchiveProps = { searchParams: Promise<{ year?: string | string[] }> };

export default async function ArchivePage({ searchParams }: ArchiveProps) {
  const [articles, requested] = await Promise.all([getPublicationIndex(5000), searchParams]);
  const grouped = new Map<string, Map<string, typeof articles>>();
  articles.forEach((article) => {
    const date = new Date(article.published_at || article.created_at);
    const year = String(date.getFullYear());
    const month = new Intl.DateTimeFormat("en-IN", { month: "long" }).format(date);
    if (!grouped.has(year)) grouped.set(year, new Map());
    const months = grouped.get(year)!;
    if (!months.has(month)) months.set(month, []);
    months.get(month)!.push(article);
  });
  const years = [...grouped.keys()].sort((a, b) => Number(b) - Number(a));
  const requestedYear = Array.isArray(requested.year) ? requested.year[0] : requested.year;
  const selectedYear = requestedYear && grouped.has(requestedYear) ? requestedYear : years[0];
  const selectedMonths = selectedYear ? grouped.get(selectedYear) : undefined;
  const selectedCount = selectedMonths ? [...selectedMonths.values()].reduce((total, stories) => total + stories.length, 0) : 0;
  const categories = [...new Set(articles.map((article) => article.category))].sort();

  return (
    <PublicShell>
      <PageHeader eyebrow="Public record" title="News archive" description={`${articles.length} published ${articles.length === 1 ? "story" : "stories"}, organized by edition and section.`} crumbs={[{ label: "Archive" }]} />
      {categories.length > 0 && <nav className="archive-categories" aria-label="Archive sections">{categories.map((category) => <Link key={category} href={`/section/${encodeURIComponent(category.toLowerCase())}`}>{category}</Link>)}</nav>}
      {years.length > 0 && <nav className="archive-year-nav" aria-label="Archive years">{years.map((year) => <Link key={year} href={`/archive?year=${year}`} aria-current={year === selectedYear ? "page" : undefined}>{year}</Link>)}</nav>}
      {articles.length === 0 ? <section className="public-empty-state"><h2>The archive is empty</h2><p>No published stories are available.</p></section> : (
        <div className="archive-years">
          {selectedMonths && <section><h2>{selectedYear} <small>{selectedCount} stories</small></h2>{[...selectedMonths.entries()].map(([month, stories], index) => <details key={month} open={index === 0}><summary>{month} <span>{stories.length}</span></summary><ol>{stories.map((article) => <li key={article.id}><time>{formatNewsDate(article.published_at || article.created_at)}</time><Link href={articleHref(article)}>{article.title}</Link><span>{article.category}</span><Link className="edition-link" href={`/edition/${(article.published_at || article.created_at).slice(0, 10)}`}>Edition</Link></li>)}</ol></details>)}</section>}
        </div>
      )}
    </PublicShell>
  );
}
