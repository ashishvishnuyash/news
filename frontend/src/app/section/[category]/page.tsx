import type { Metadata } from "next";
import ArticleCard from "../../components/ArticleCard";
import NewsletterSignup from "../../components/NewsletterSignup";
import PageHeader from "../../components/PageHeader";
import PublicShell from "../../components/PublicShell";
import AnalyticsEvent from "../../components/AnalyticsEvent";
import { getSiteSettings, searchArticles } from "../../../lib/news";

type SectionProps = { params: Promise<{ category: string }> };
const labelFor = (value: string) => decodeURIComponent(value).split("-").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
export async function generateMetadata({ params }: SectionProps): Promise<Metadata> { const { category } = await params; const label = labelFor(category); return { title: label, description: `Latest ${label} reporting from The Republic Bulletin.` }; }

export default async function SectionPage({ params }: SectionProps) {
  const { category } = await params;
  const label = labelFor(category);
  const [result, settings] = await Promise.all([searchArticles({ category: label, limit: 50, sort: "newest" }), getSiteSettings()]);
  return <PublicShell currentCategory={label}><AnalyticsEvent name="category_view" properties={{ category: label, result_count: result.total }} /><PageHeader eyebrow="News section" title={label} description={`Latest reporting and analysis filed under ${label}.`} crumbs={[{ label }]} />{result.items.length ? <div className="search-results">{result.items.map((article) => <ArticleCard key={article.id} article={article} />)}</div> : <section className="public-empty-state"><h2>No published {label} stories</h2><p>The newsroom has not filed a story in this section yet.</p></section>}{settings.newsletter?.enabled !== false && <NewsletterSignup name={settings.newsletter?.name} description={settings.newsletter?.description} source={`section-${category}`} />}</PublicShell>;
}
