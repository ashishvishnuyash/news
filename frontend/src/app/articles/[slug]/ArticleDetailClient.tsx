"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import AdSlot from "../../components/AdSlot";
import ArticleCard from "../../components/ArticleCard";
import Header from "../../components/Header";
import NewsletterSignup from "../../components/NewsletterSignup";
import { apiFetch } from "../../../lib/auth";
import { apiUrl } from "../../../lib/config";
import { authorHref, formatNewsDate, readingMinutes, splitEditorialList } from "../../../lib/news";
import { trackEvent } from "../../../lib/analytics";
import type { Article, Correction, SiteSettings } from "../../../lib/types";

interface CurrentUser { id: number; username: string; role: string }
interface Comment { id: number; content: string; created_at: string; author: { id: number; username: string; role: string } }

function escapeHtml(value: string) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;").replace(/'/g, "&#039;");
}

function formatInlineMarkdown(text: string) {
  return escapeHtml(text).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\*(.*?)\*/g, "<em>$1</em>").replace(/`([^`]+)`/g, "<code>$1</code>");
}

function getContentHtml(content: string) {
  if (!content) return "";
  if (content.trim().startsWith("<")) return content;
  return content.split(/\n\n+/).map((block) => {
    const trimmed = block.trim();
    if (!trimmed) return "";
    if (trimmed.startsWith("### ")) return `<h3>${formatInlineMarkdown(trimmed.slice(4))}</h3>`;
    if (trimmed.startsWith("## ")) return `<h2>${formatInlineMarkdown(trimmed.slice(3))}</h2>`;
    if (trimmed.startsWith("# ")) return `<h1>${formatInlineMarkdown(trimmed.slice(2))}</h1>`;
    if (trimmed.split("\n").every((line) => /^[-*]\s/.test(line.trim()))) return `<ul>${trimmed.split("\n").map((line) => `<li>${formatInlineMarkdown(line.trim().replace(/^[-*]\s+/, ""))}</li>`).join("")}</ul>`;
    return `<p>${formatInlineMarkdown(trimmed)}</p>`;
  }).join("");
}

export default function ArticleDetailClient({
  articleSlug,
  initialArticle,
  relatedStories,
  moreFromAuthor,
  mostRead,
  corrections,
  settings,
}: {
  articleSlug: string;
  initialArticle: Article;
  relatedStories: Article[];
  moreFromAuthor: Article[];
  mostRead: Article[];
  corrections: Correction[];
  settings: SiteSettings;
}) {
  const [article, setArticle] = useState<Article>(initialArticle);
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [commentLoading, setCommentLoading] = useState(false);
  const [commentError, setCommentError] = useState("");
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
  const [editingCommentText, setEditingCommentText] = useState("");
  const [shareNotice, setShareNotice] = useState("");
  const [shareUrl, setShareUrl] = useState("");
  const commentsEnabled = settings.features?.comments_enabled !== false;
  const tags = useMemo(() => article.tags?.split(",").map((tag) => tag.trim()).filter(Boolean) || [], [article.tags]);
  const sources = useMemo(() => splitEditorialList(article.sources), [article.sources]);

  const fetchArticle = useCallback(async () => {
    try {
      const response = await fetch(apiUrl(`/api/articles/${articleSlug}`));
      if (response.ok) setArticle(await response.json());
    } catch {
      // The server-rendered article remains readable when a view-count refresh fails.
    }
  }, [articleSlug]);

  const fetchComments = useCallback(async () => {
    try {
      const response = await fetch(apiUrl(`/api/articles/${articleSlug}/comments`));
      if (response.ok) setComments(await response.json());
    } catch {
      setCommentError("Reader responses are temporarily unavailable.");
    }
  }, [articleSlug]);

  const fetchUser = useCallback(async () => {
    try {
      const response = await apiFetch(apiUrl("/api/auth/me"));
      if (response.ok) setUser(await response.json());
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    setShareUrl(window.location.href);
    trackEvent("article_view", { article_id: initialArticle.id, category: initialArticle.category, article_type: initialArticle.article_type });
    const timer = window.setTimeout(() => { void fetchArticle(); void fetchComments(); void fetchUser(); }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchArticle, fetchComments, fetchUser, initialArticle.article_type, initialArticle.category, initialArticle.id]);

  const postComment = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newComment.trim()) return;
    setCommentLoading(true); setCommentError("");
    try {
      const response = await apiFetch(apiUrl(`/api/articles/${articleSlug}/comments`), { method: "POST", body: JSON.stringify({ content: newComment.trim() }) });
      if (!response.ok) throw new Error(await response.json().then((data) => data.detail).catch(() => "Response could not be posted."));
      setNewComment(""); await fetchComments();
    } catch (error) { setCommentError(error instanceof Error ? error.message : "Response could not be posted."); }
    finally { setCommentLoading(false); }
  };

  const editComment = async (commentId: number) => {
    if (!editingCommentText.trim()) return;
    const response = await apiFetch(apiUrl(`/api/articles/${articleSlug}/comments/${commentId}`), { method: "PUT", body: JSON.stringify({ content: editingCommentText.trim() }) });
    if (response.ok) { setEditingCommentId(null); setEditingCommentText(""); await fetchComments(); }
    else setCommentError(await response.json().then((data) => data.detail).catch(() => "Response could not be edited."));
  };

  const deleteComment = async (commentId: number) => {
    if (!window.confirm("Delete this response from the public record?")) return;
    const response = await apiFetch(apiUrl(`/api/articles/${articleSlug}/comments/${commentId}`), { method: "DELETE" });
    if (response.ok) await fetchComments(); else setCommentError("Response could not be deleted.");
  };

  const copyOrShare = async () => {
    try {
      const usedNativeShare = typeof navigator.share === "function";
      if (usedNativeShare) await navigator.share({ title: article.title, text: article.summary || article.subtitle || undefined, url: window.location.href });
      else await navigator.clipboard.writeText(window.location.href);
      setShareNotice(usedNativeShare ? "Shared" : "Link copied");
      trackEvent("article_share", { article_id: article.id, channel: usedNativeShare ? "native" : "copy" });
      window.setTimeout(() => setShareNotice(""), 2500);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) setShareNotice("Could not share");
    }
  };

  const encodedUrl = encodeURIComponent(shareUrl);
  const encodedTitle = encodeURIComponent(article.title);
  const recordShare = (channel: string) => trackEvent("article_share", { article_id: article.id, channel });

  return (
    <div className="trb-container public-shell">
      <Header currentCategory={article.category} initialSettings={settings} />
      <main id="main-content" className="article-layout">
        <article className="article-main">
          <nav className="breadcrumbs" aria-label="Breadcrumb"><Link href="/">Home</Link><span><Link href={`/section/${encodeURIComponent(article.category.toLowerCase())}`}>{article.category}</Link></span><span>Article</span></nav>
          <header className="article-header">
            <p className="story-kicker">{article.article_type.replace("_", " ")}{article.fact_check_rating ? ` · ${article.fact_check_rating.replace("_", " ")}` : ""}</p>
            <h1>{article.title}</h1>
            {article.subtitle && <p className="article-subtitle">{article.subtitle}</p>}
            {article.summary && <p className="article-deck">{article.summary}</p>}
            <div className="article-byline">
              <div className="author-mark" aria-hidden="true">{article.author.username.charAt(0).toUpperCase()}</div>
              <div><span>By <Link href={authorHref(article.author)}>{article.author.username}</Link></span>{article.author.job_title && <small>{article.author.job_title}</small>}</div>
            </div>
            <dl className="article-dates">
              <div><dt>Published</dt><dd><time dateTime={article.published_at || article.created_at}>{formatNewsDate(article.published_at || article.created_at, true)}</time></dd></div>
              <div><dt>Updated</dt><dd><time dateTime={article.updated_at}>{formatNewsDate(article.updated_at, true)}</time></dd></div>
              <div><dt>Reading time</dt><dd>{readingMinutes(article.content)} min read</dd></div>
              <div><dt>Views</dt><dd>{article.view_count || 0}</dd></div>
            </dl>
            <div className="share-bar" aria-label="Share this article">
              <span>Share</span>
              <a href={`https://wa.me/?text=${encodedTitle}%20${encodedUrl}`} target="_blank" rel="noreferrer" onClick={() => recordShare("whatsapp")}>WhatsApp</a>
              <a href={`https://twitter.com/intent/tweet?text=${encodedTitle}&url=${encodedUrl}`} target="_blank" rel="noreferrer" onClick={() => recordShare("x")}>X</a>
              <a href={`https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`} target="_blank" rel="noreferrer" onClick={() => recordShare("facebook")}>Facebook</a>
              <a href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`} target="_blank" rel="noreferrer" onClick={() => recordShare("linkedin")}>LinkedIn</a>
              <button type="button" onClick={copyOrShare}>{shareNotice || "Copy link"}</button>
              <button type="button" onClick={() => window.print()}>Print</button>
            </div>
          </header>

          {article.image_url && <figure className="article-hero"><Image src={article.image_url} alt={article.image_caption || article.title} width={1200} height={720} priority />{article.image_caption && <figcaption>{article.image_caption}</figcaption>}</figure>}
          <div className="article-prose" dangerouslySetInnerHTML={{ __html: getContentHtml(article.content) }} />

          {sources.length > 0 && <section className="article-sources" aria-labelledby="sources-heading"><h2 id="sources-heading">Sources and references</h2><ol>{sources.map((source, index) => <li key={`${source}-${index}`}>{/^https?:\/\//i.test(source) ? <a href={source} target="_blank" rel="noreferrer">{source}</a> : source}</li>)}</ol></section>}
          {corrections.length > 0 && <section className="article-corrections" aria-labelledby="corrections-heading"><h2 id="corrections-heading">Corrections</h2>{corrections.map((item) => <article key={item.id}><time dateTime={item.created_at}>{formatNewsDate(item.created_at, true)}</time><p><strong>{item.summary}</strong></p>{item.details && <p>{item.details}</p>}</article>)}<Link href="/corrections">View correction ledger</Link></section>}
          {tags.length > 0 && <nav className="article-tags" aria-label="Article tags"><span>Filed under</span>{tags.map((tag) => <Link key={tag} href={`/search?q=${encodeURIComponent(tag)}`}>{tag}</Link>)}</nav>}
          <AdSlot slot="article" settings={settings} />
        </article>

        <aside className="article-sidebar" aria-label="Related reporting">
          <section><p className="eyebrow">Reader interest</p><h2>Most read</h2><ol className="article-most-read">{mostRead.map((item, index) => <li key={item.id}><span>{index + 1}</span><ArticleCard article={item} compact /></li>)}</ol></section>
          <AdSlot slot="sidebar" settings={settings} />
        </aside>
      </main>

      {relatedStories.length > 0 && <section className="article-recommendations"><div className="section-heading"><div><p className="eyebrow">Continue reading</p><h2>Related stories</h2></div></div><div>{relatedStories.map((item) => <ArticleCard key={item.id} article={item} />)}</div></section>}
      {moreFromAuthor.length > 0 && <section className="article-recommendations"><div className="section-heading"><div><p className="eyebrow">Newsroom</p><h2>More from {article.author.username}</h2></div><Link href={authorHref(article.author)}>Author profile</Link></div><div>{moreFromAuthor.map((item) => <ArticleCard key={item.id} article={item} compact />)}</div></section>}
      {settings.newsletter?.enabled !== false && <NewsletterSignup name={settings.newsletter?.name || "The Republic Brief"} description={settings.newsletter?.description || "The biggest stories you need to know today, selected by the newsroom."} source={`article-${article.id}`} />}

      <section className="comments-section" aria-labelledby="comments-heading">
        <div className="section-heading"><div><p className="eyebrow">Public record</p><h2 id="comments-heading">Reader responses</h2></div><span>{comments.length} filed</span></div>
        {!commentsEnabled ? <p className="configuration-note">Reader responses are closed for this edition.</p> : user ? <form className="comment-form" onSubmit={postComment}><label htmlFor="new-comment">Respond as {user.username}</label><textarea id="new-comment" value={newComment} onChange={(event) => setNewComment(event.target.value)} maxLength={2000} required disabled={commentLoading} />{commentError && <p className="form-alert" role="alert">{commentError}</p>}<button className="trb-btn-solid" disabled={commentLoading}>{commentLoading ? "Publishing…" : "Post response"}</button></form> : <div className="comment-login"><p>Sign in to add a public response.</p><Link href={`/login?next=${encodeURIComponent(`/articles/${articleSlug}`)}`} className="trb-btn-solid">Sign in</Link></div>}
        <div className="comment-list">{comments.length === 0 ? <p className="configuration-note">No public responses have been filed.</p> : comments.map((comment) => <article key={comment.id}><header><strong>{comment.author.username}</strong><span>{comment.author.role.replace("_", " ")}</span><time dateTime={comment.created_at}>{formatNewsDate(comment.created_at, true)}</time></header>{editingCommentId === comment.id ? <div className="comment-edit-form"><textarea value={editingCommentText} onChange={(event) => setEditingCommentText(event.target.value)} maxLength={2000} /><button className="trb-btn-solid" onClick={() => void editComment(comment.id)}>Save</button><button className="trb-btn-pill" onClick={() => setEditingCommentId(null)}>Cancel</button></div> : <p>{comment.content}</p>}{user && (user.id === comment.author.id || ["ADMIN", "SUPER_ADMIN"].includes(user.role)) && editingCommentId !== comment.id && <div className="comment-actions"><button onClick={() => { setEditingCommentId(comment.id); setEditingCommentText(comment.content); }}>Edit</button><button className="danger" onClick={() => void deleteComment(comment.id)}>Delete</button></div>}</article>)}</div>
      </section>

      <footer className="public-footer compact"><nav><Link href="/about">About</Link><Link href="/editorial-standards">Editorial standards</Link><Link href="/corrections">Corrections</Link><Link href="/contact">Contact</Link></nav></footer>
    </div>
  );
}
