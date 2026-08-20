import Image from "next/image";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import AnalyticsEvent from "../../components/AnalyticsEvent";
import ArticleCard from "../../components/ArticleCard";
import JsonLd from "../../components/JsonLd";
import PageHeader from "../../components/PageHeader";
import PublicShell from "../../components/PublicShell";
import { absoluteUrl, getAuthor, splitEditorialList } from "../../../lib/news";
import { siteUrl } from "../../../lib/config";

type AuthorProps = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: AuthorProps): Promise<Metadata> {
  const { slug } = await params;
  const profile = await getAuthor(slug);
  if (!profile) return { title: "Author not found", robots: { index: false } };
  return { title: profile.author.username, description: profile.author.bio || `Reporting by ${profile.author.username} for The Republic Bulletin.` };
}

export default async function AuthorPage({ params }: AuthorProps) {
  const { slug } = await params;
  const profile = await getAuthor(slug);
  if (!profile) notFound();
  const profileLinks = splitEditorialList(profile.author.social_links).filter((item) => /^https?:\/\//i.test(item));
  const person = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: profile.author.username,
    url: siteUrl(`/authors/${profile.author.slug || profile.author.username}`),
    ...(profile.author.job_title ? { jobTitle: profile.author.job_title } : {}),
    ...(profile.author.profile_image_url ? { image: absoluteUrl(profile.author.profile_image_url) } : {}),
    ...(profileLinks.length ? { sameAs: profileLinks } : {}),
  };

  return (
    <PublicShell>
      <AnalyticsEvent name="author_page_view" properties={{ author_id: profile.author.id }} />
      <JsonLd data={person} />
      <PageHeader eyebrow="Newsroom directory" title={profile.author.username} crumbs={[{ label: "Authors" }, { label: profile.author.username }]} />
      <section className="author-profile">
        {profile.author.profile_image_url ? <Image src={profile.author.profile_image_url} alt={profile.author.username} width={260} height={260} /> : <div className="author-initial" aria-hidden="true">{profile.author.username.charAt(0).toUpperCase()}</div>}
        <div>
          <p className="author-role">{profile.author.job_title || profile.author.role.replace("_", " ")}</p>
          {profile.author.bio ? <p>{profile.author.bio}</p> : <p className="configuration-note">This author has not added a public biography.</p>}
          <dl><dt>Published stories</dt><dd>{profile.total_articles}</dd><dt>Total reads</dt><dd>{profile.total_views}</dd></dl>
          {profile.coverage_areas.length > 0 && <div className="author-coverage"><strong>Areas of coverage</strong>{profile.coverage_areas.map((area) => <span key={area}>{area}</span>)}</div>}
          {profileLinks.length > 0 && <nav className="author-links" aria-label={`${profile.author.username} profiles`}>{profileLinks.map((url) => <a key={url} href={url} target="_blank" rel="me noreferrer">Public profile</a>)}</nav>}
        </div>
      </section>
      <div className="section-heading"><div><p className="eyebrow">By this author</p><h2>Published reporting</h2></div></div>
      {profile.articles.length ? <div className="search-results">{profile.articles.map((article) => <ArticleCard key={article.id} article={article} />)}</div> : <section className="public-empty-state"><h2>No published stories</h2></section>}
    </PublicShell>
  );
}
