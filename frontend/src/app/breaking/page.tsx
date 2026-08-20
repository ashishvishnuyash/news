import type { Metadata } from "next";
import ArticleCard from "../components/ArticleCard";
import PageHeader from "../components/PageHeader";
import PublicShell from "../components/PublicShell";
import { searchArticles } from "../../lib/news";

export const metadata: Metadata = { title: "Breaking News", description: "Current breaking coverage from The Republic Bulletin." };
export default async function BreakingPage() { const result = await searchArticles({ breaking_only: true, limit: 50, sort: "newest" }); return <PublicShell><PageHeader eyebrow="Developing stories" title="Breaking news" description="Only stories explicitly marked by editors as breaking appear here." crumbs={[{ label: "Breaking news" }]} />{result.items.length ? <div className="search-results">{result.items.map((article) => <ArticleCard key={article.id} article={article} />)}</div> : <section className="public-empty-state"><h2>No active breaking stories</h2><p>Editors have not marked any current coverage as breaking.</p></section>}</PublicShell>; }
