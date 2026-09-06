import type { Metadata } from "next";
import { notFound } from "next/navigation";
import JsonLd from "../../components/JsonLd";
import {
  absoluteUrl,
  authorHref,
  getArticle,
  getAuthor,
  getCorrections,
  getMostRead,
  getSiteSettings,
  searchArticles,
} from "../../../lib/news";
import { siteUrl } from "../../../lib/config";
import ArticleDetailClient from "./ArticleDetailClient";

type ArticlePageProps = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: ArticlePageProps): Promise<Metadata> {
  const { slug } = await params;
  const article = await getArticle(slug);
  if (!article) return { title: "Dispatch not found", robots: { index: false, follow: false } };
  const description = article.seo_description?.trim() || article.summary?.trim() || article.subtitle?.trim() || `Read ${article.title} in The Republic Bulletin.`;
  const canonicalPath = `/articles/${article.slug || slug}`;
  const socialImage = absoluteUrl(article.og_image_url || article.image_url) || siteUrl("/favicon.png");
  const socialImages = [{ url: socialImage, alt: article.image_caption?.trim() || article.title }];
  return {
    title: article.seo_title || article.title,
    description,
    alternates: { canonical: canonicalPath },
    authors: [{ name: article.author.username, url: authorHref(article.author) }],
    creator: article.author.username,
    publisher: "The Republic Bulletin",
    category: article.category,
    keywords: article.tags?.split(",").map((tag) => tag.trim()).filter(Boolean),
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        "max-image-preview": "large",
        "max-snippet": -1,
        "max-video-preview": -1,
      },
    },
    openGraph: {
      type: "article",
      url: siteUrl(canonicalPath),
      title: article.seo_title || article.title,
      description,
      siteName: "The Republic Bulletin",
      locale: "en_IN",
      images: socialImages,
      publishedTime: article.published_at || article.created_at,
      modifiedTime: article.updated_at,
      authors: [article.author.username],
      section: article.category,
      tags: article.tags?.split(",").map((tag) => tag.trim()).filter(Boolean),
    },
    twitter: {
      card: "summary_large_image",
      title: article.seo_title || article.title,
      description,
      images: socialImages,
    },
  };
}

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { slug } = await params;
  const article = await getArticle(slug);
  if (!article) notFound();
  const [relatedResult, authorProfile, mostRead, corrections, settings] = await Promise.all([
    searchArticles({ category: article.category, limit: 8, sort: "newest" }),
    getAuthor(article.author.slug || article.author.username),
    getMostRead(6),
    getCorrections(),
    getSiteSettings(),
  ]);
  const image = absoluteUrl(article.og_image_url || article.image_url);
  const canonical = siteUrl(`/articles/${article.slug || slug}`);
  const newsArticle = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: article.title,
    ...(article.subtitle ? { alternativeHeadline: article.subtitle } : {}),
    description: article.seo_description || article.summary || article.subtitle,
    ...(image ? { image: [image] } : {}),
    ...(image ? { thumbnailUrl: image } : {}),
    datePublished: article.published_at || article.created_at,
    dateModified: article.updated_at,
    articleSection: article.category,
    inLanguage: "en-IN",
    ...(article.tags ? { keywords: article.tags } : {}),
    mainEntityOfPage: { "@type": "WebPage", "@id": canonical },
    author: { "@type": "Person", name: article.author.username, url: siteUrl(authorHref(article.author)) },
    publisher: { "@type": "NewsMediaOrganization", name: settings.site_name, url: siteUrl("/"), logo: { "@type": "ImageObject", url: siteUrl("/icon.png") } },
    isAccessibleForFree: true,
  };
  const breadcrumbs = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: siteUrl("/") },
      { "@type": "ListItem", position: 2, name: article.category, item: siteUrl(`/section/${encodeURIComponent(article.category.toLowerCase())}`) },
      { "@type": "ListItem", position: 3, name: article.title, item: canonical },
    ],
  };
  return (
    <>
      <JsonLd data={[newsArticle, breadcrumbs]} />
      <ArticleDetailClient
        articleSlug={slug}
        initialArticle={article}
        relatedStories={relatedResult.items.filter((item) => item.id !== article.id).slice(0, 4)}
        moreFromAuthor={(authorProfile?.articles || []).filter((item) => item.id !== article.id).slice(0, 4)}
        mostRead={mostRead.filter((item) => item.id !== article.id).slice(0, 5)}
        corrections={corrections.filter((item) => item.article_id === article.id)}
        settings={settings}
      />
    </>
  );
}
