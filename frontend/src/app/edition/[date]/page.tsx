import type { Metadata } from "next";
import { notFound } from "next/navigation";
import ArticleCard from "../../components/ArticleCard";
import PageHeader from "../../components/PageHeader";
import PublicShell from "../../components/PublicShell";
import { searchArticles } from "../../../lib/news";

type EditionProps = { params: Promise<{ date: string }> };

export async function generateMetadata({ params }: EditionProps): Promise<Metadata> {
  const { date } = await params;
  return { title: `Edition · ${date}`, description: `The Republic Bulletin edition for ${date}.` };
}

export default async function EditionPage({ params }: EditionProps) {
  const { date } = await params;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(Date.parse(`${date}T00:00:00`))) notFound();
  const result = await searchArticles({ date_from: `${date}T00:00:00`, date_to: `${date}T23:59:59`, limit: 50, sort: "newest" });
  const label = new Intl.DateTimeFormat("en-IN", { dateStyle: "full", timeZone: "UTC" }).format(new Date(`${date}T00:00:00Z`));
  return <PublicShell><PageHeader eyebrow="Daily edition" title={label} description={`${result.total} published ${result.total === 1 ? "story" : "stories"} in this edition.`} crumbs={[{ label: "Archive", href: "/archive" }, { label: date }]} />{result.items.length ? <div className="search-results">{result.items.map((article) => <ArticleCard key={article.id} article={article} />)}</div> : <section className="public-empty-state"><h2>No edition was published</h2><p>There are no published stories for this date.</p></section>}</PublicShell>;
}
