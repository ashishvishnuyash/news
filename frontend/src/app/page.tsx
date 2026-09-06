import Image from "next/image";
import Link from "next/link";
import AdSlot from "./components/AdSlot";
import ArticleCard from "./components/ArticleCard";
import JsonLd from "./components/JsonLd";
import NewsletterSignup from "./components/NewsletterSignup";
import OnboardingTour from "./components/OnboardingTour";
import PublicShell from "./components/PublicShell";
import {
  articleHref,
  articlePreview,
  authorHref,
  formatNewsDate,
  getMostRead,
  getSiteSettings,
  searchArticles,
} from "../lib/news";
import { siteUrl } from "../lib/config";

const SECTION_ORDER = [
  "India", "World", "Politics", "Business", "Economy", "Technology",
  "Science", "Culture", "Sports", "Opinion", "Investigations", "Fact Check",
];

export default async function Home() {
  const [latestResult, mostRead, settings] = await Promise.all([
    searchArticles({ limit: 50, sort: "newest" }),
    getMostRead(6),
    getSiteSettings(),
  ]);
  const articles = latestResult.items;
  const featured = articles.find((article) => article.is_pinned) || articles[0];
  const latest = articles.filter((article) => article.id !== featured?.id).slice(0, 8);
  const breaking = articles.filter((article) => article.is_breaking).slice(0, 4);
  const availableSections = SECTION_ORDER.map((label) => ({
    label,
    articles: articles.filter((article) => {
      const normalized = article.category.toLowerCase();
      if (label === "Business") return normalized === "business" || normalized === "economy";
      if (label === "Investigations") return article.article_type === "INVESTIGATION" || normalized === "investigations";
      if (label === "Fact Check") return article.article_type === "FACT_CHECK" || normalized === "fact check";
      return normalized === label.toLowerCase();
    }).slice(0, 4),
  })).filter((section) => section.articles.length > 0);

  const organization = {
    "@context": "https://schema.org",
    "@type": "NewsMediaOrganization",
    name: settings.site_name,
    url: siteUrl("/"),
    logo: siteUrl("/icon.png"),
    publishingPrinciples: siteUrl("/editorial-standards"),
    correctionsPolicy: siteUrl("/corrections"),
  };

  return (
    <PublicShell>
      <JsonLd data={organization} />
      <AdSlot slot="header" settings={settings} />

      {breaking.length > 0 && (
        <section className="breaking-desk" aria-labelledby="breaking-heading">
          <div><p className="eyebrow">Developing</p><h2 id="breaking-heading">Breaking news</h2></div>
          <ol>{breaking.map((article) => <li key={article.id}><Link href={articleHref(article)}>{article.title}</Link></li>)}</ol>
          <Link href="/breaking">All breaking coverage</Link>
        </section>
      )}

      {!featured ? (
        <section className="public-empty-state">
          <p className="eyebrow">Pressroom</p>
          <h1>No published stories yet</h1>
          <p>The newsroom has not published an edition. Draft and review activity remains private.</p>
        </section>
      ) : (
        <>
          <section className={`home-lead ${!featured.image_url ? "has-no-image" : ""}`} aria-labelledby="top-story-heading">
            <div className="home-lead-copy">
              <p className="story-kicker">{featured.is_breaking ? "Breaking · " : ""}{featured.category}</p>
              <h1 id="top-story-heading"><Link href={articleHref(featured)}>{featured.title}</Link></h1>
              {featured.subtitle && <p className="home-deck">{featured.subtitle}</p>}
              <p>{articlePreview(featured, 360)}</p>
              <div className="story-byline">
                <span>By <Link href={authorHref(featured.author)}>{featured.author.username}</Link></span>
                <time dateTime={featured.published_at || featured.created_at}>{formatNewsDate(featured.published_at || featured.created_at, true)}</time>
              </div>
              <Link href={articleHref(featured)} className="trb-btn-solid home-read-link">Read the full report</Link>
            </div>
            {featured.image_url && (
              <figure>
                <Link href={articleHref(featured)}><Image src={featured.image_url} alt={featured.image_caption || featured.title} width={900} height={560} priority /></Link>
                {featured.image_caption && <figcaption>{featured.image_caption}</figcaption>}
              </figure>
            )}
          </section>

          <div className="home-news-grid">
            <section aria-labelledby="latest-heading">
              <div className="section-heading"><div><p className="eyebrow">The latest</p><h2 id="latest-heading">Latest news</h2></div><Link href="/search?sort=newest">View all</Link></div>
              <div className="latest-grid">{latest.map((article) => <ArticleCard key={article.id} article={article} />)}</div>
            </section>
            <aside className="most-read" aria-labelledby="most-read-heading">
              <div className="section-heading"><div><p className="eyebrow">Reader interest</p><h2 id="most-read-heading">Most read</h2></div></div>
              <ol>{mostRead.map((article, index) => <li key={article.id}><span>{String(index + 1).padStart(2, "0")}</span><ArticleCard article={article} compact /></li>)}</ol>
              <AdSlot slot="sidebar" settings={settings} />
            </aside>
          </div>

          <AdSlot slot="in_feed" settings={settings} />

          <div className="home-sections">
            {availableSections.map((section) => (
              <section key={section.label} aria-labelledby={`section-${section.label.replace(/\s+/g, "-").toLowerCase()}`}>
                <div className="section-heading">
                  <div><p className="eyebrow">Section</p><h2 id={`section-${section.label.replace(/\s+/g, "-").toLowerCase()}`}>{section.label}</h2></div>
                  <Link href={section.label === "Fact Check" ? "/fact-check" : `/section/${encodeURIComponent(section.label.toLowerCase())}`}>More {section.label}</Link>
                </div>
                <div className="section-story-grid">{section.articles.map((article) => <ArticleCard key={article.id} article={article} compact={section.articles.length > 2} />)}</div>
              </section>
            ))}
          </div>

          {settings.newsletter?.enabled !== false && <NewsletterSignup
            name={settings.newsletter?.name || "The Republic Brief"}
            description={settings.newsletter?.description || "The biggest stories you need to know today, selected by the newsroom."}
            source="homepage"
          />}

          <section className="archive-callout">
            <div><p className="eyebrow">Public record</p><h2>Browse the archive</h2><p>Explore published reporting by year, month, and section.</p></div>
            <Link href="/archive" className="trb-btn-solid">Open the archive</Link>
          </section>
        </>
      )}
      <OnboardingTour />
    </PublicShell>
  );
}
