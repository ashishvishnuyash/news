import type { Metadata } from "next";
import ArticleCard from "../components/ArticleCard";
import PageHeader from "../components/PageHeader";
import PublicShell from "../components/PublicShell";
import { searchArticles } from "../../lib/news";

export const metadata: Metadata = { title: "Fact Check", description: "Evidence-based fact checks published by The Republic Bulletin." };
export default async function FactCheckPage() { const [typed, legacy] = await Promise.all([searchArticles({ article_type: "FACT_CHECK", limit: 50 }), searchArticles({ category: "Fact Check", limit: 50 })]); const items = [...typed.items, ...legacy.items].filter((article, index, all) => all.findIndex((candidate) => candidate.id === article.id) === index); return <PublicShell currentCategory="Fact Check"><PageHeader eyebrow="Verification desk" title="Fact check" description="Claims are rated only when an article explains the evidence and identifies its sources." crumbs={[{ label: "Fact Check" }]} />{items.length ? <div className="search-results">{items.map((article) => <ArticleCard key={article.id} article={article} />)}</div> : <section className="public-empty-state"><h2>No fact checks published</h2><p>The verification desk has no published records yet.</p></section>}</PublicShell>; }
