"use client";

import Image from "next/image";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import RichTextEditor from "../../components/RichTextEditor";
import { apiErrorMessage, apiFetch } from "../../../lib/auth";
import { apiUrl, siteUrl } from "../../../lib/config";
import type { Article, ArticleStatus } from "../../../lib/types";

interface ReviewComment {
  id: number;
  content: string;
  created_at: string;
  author: { username: string; role: string };
}

interface EditorForm {
  title: string;
  summary: string;
  content: string;
  category: string;
  image_url: string;
  image_caption: string;
  tags: string;
  is_pinned: boolean;
  is_breaking: boolean;
}

type StatusFilter = ArticleStatus | "ALL";
type Notice = { type: "success" | "error"; text: string };

const STATUS_OPTIONS: StatusFilter[] = ["ALL", "SUBMITTED", "DRAFT", "REJECTED", "PUBLISHED"];

const STATUS_COLOR: Record<ArticleStatus, string> = {
  PUBLISHED: "#35613d",
  DRAFT: "#666",
  SUBMITTED: "#214c7a",
  REJECTED: "var(--accent-red)",
};

function formFromArticle(article: Article): EditorForm {
  return {
    title: article.title,
    summary: article.summary || "",
    content: article.content,
    category: article.category,
    image_url: article.image_url || "",
    image_caption: article.image_caption || "",
    tags: article.tags || "",
    is_pinned: article.is_pinned,
    is_breaking: article.is_breaking,
  };
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function EditorQueue() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [reviews, setReviews] = useState<ReviewComment[]>([]);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("SUBMITTED");
  const [search, setSearch] = useState("");
  const [feedback, setFeedback] = useState("");
  const [editing, setEditing] = useState(false);
  const [editorForm, setEditorForm] = useState<EditorForm | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);

  const loadQueue = useCallback(async (showLoader = true) => {
    if (showLoader) setLoading(true);
    try {
      // This endpoint returns the complete editorial archive and is supported by
      // both the current API and older deployments that treat `ALL` as a literal status.
      const response = await apiFetch(apiUrl("/api/admin/articles"));
      if (!response.ok) throw new Error(await apiErrorMessage(response, "Could not load the editorial queue."));
      const data: Article[] = await response.json();
      setArticles(data);
      setSelectedArticle((current) => current ? data.find((article) => article.id === current.id) || null : null);
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Could not load the editorial queue." });
    } finally {
      if (showLoader) setLoading(false);
    }
  }, []);

  const loadReviews = useCallback(async (articleId: number) => {
    try {
      const response = await apiFetch(apiUrl(`/api/articles/${articleId}/reviews`));
      if (!response.ok) throw new Error(await apiErrorMessage(response, "Could not load editorial notes."));
      setReviews(await response.json());
    } catch (error) {
      setReviews([]);
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Could not load editorial notes." });
    }
  }, []);

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  const counts = useMemo(() => {
    const values: Record<StatusFilter, number> = { ALL: articles.length, DRAFT: 0, SUBMITTED: 0, PUBLISHED: 0, REJECTED: 0 };
    articles.forEach((article) => { values[article.status] += 1; });
    return values;
  }, [articles]);

  const visibleArticles = useMemo(() => {
    const query = search.trim().toLowerCase();
    return articles.filter((article) => {
      const statusMatches = statusFilter === "ALL" || article.status === statusFilter;
      const searchMatches = !query || [article.title, article.summary, article.category, article.tags, article.author.username]
        .some((value) => value?.toLowerCase().includes(query));
      return statusMatches && searchMatches;
    });
  }, [articles, search, statusFilter]);

  const selectArticle = (article: Article) => {
    setSelectedArticle(article);
    setEditing(false);
    setEditorForm(null);
    setFeedback("");
    setNotice(null);
    void loadReviews(article.id);
  };

  const updateArticle = async (payload: Record<string, unknown>, successMessage: string) => {
    if (!selectedArticle) return false;
    setBusy(true);
    setNotice(null);
    try {
      const response = await apiFetch(apiUrl(`/api/articles/${selectedArticle.id}`), {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(await apiErrorMessage(response, "The article could not be updated."));
      const updated: Article = await response.json();
      setArticles((current) => current.map((article) => article.id === updated.id ? updated : article));
      setSelectedArticle(updated);
      setNotice({ type: "success", text: successMessage });
      await loadQueue(false);
      return true;
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "The article could not be updated." });
      return false;
    } finally {
      setBusy(false);
    }
  };

  const changeStatus = async (status: ArticleStatus) => {
    if (!selectedArticle) return;
    const prompts: Record<ArticleStatus, string> = {
      PUBLISHED: "Publish this story to the live front page now?",
      DRAFT: selectedArticle.status === "PUBLISHED" ? "Unpublish this story and return it to draft?" : "Move this story back to draft?",
      SUBMITTED: "Place this story in the editorial review queue?",
      REJECTED: "Return this story to the writer for revision?",
    };
    if (!window.confirm(prompts[status])) return;
    const messages: Record<ArticleStatus, string> = {
      PUBLISHED: "The story is now published.",
      DRAFT: "The story was moved to draft.",
      SUBMITTED: "The story was moved into editorial review.",
      REJECTED: "The story was returned to the writer.",
    };
    await updateArticle({ status }, messages[status]);
  };

  const openEditor = () => {
    if (!selectedArticle) return;
    setEditorForm(formFromArticle(selectedArticle));
    setEditing(true);
  };

  const saveEdits = async (event: FormEvent) => {
    event.preventDefault();
    if (!editorForm) return;
    const saved = await updateArticle({
      ...editorForm,
      title: editorForm.title.trim(),
      summary: editorForm.summary.trim(),
      category: editorForm.category.trim(),
      image_url: editorForm.image_url.trim() || null,
      image_caption: editorForm.image_url.trim() ? editorForm.image_caption.trim() || null : null,
      tags: editorForm.tags.trim() || null,
    }, "Editorial changes were saved.");
    if (saved) {
      setEditing(false);
      setEditorForm(null);
    }
  };

  const sendNote = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedArticle || !feedback.trim()) return;
    setBusy(true);
    setNotice(null);
    try {
      const response = await apiFetch(apiUrl(`/api/articles/${selectedArticle.id}/reviews`), {
        method: "POST",
        body: JSON.stringify({ content: feedback.trim() }),
      });
      if (!response.ok) throw new Error(await apiErrorMessage(response, "The editorial note could not be sent."));
      setFeedback("");
      await loadReviews(selectedArticle.id);
      setNotice({ type: "success", text: "Editorial note sent to the writer." });
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "The editorial note could not be sent." });
    } finally {
      setBusy(false);
    }
  };

  const rejectWithFeedback = async () => {
    if (!selectedArticle || !feedback.trim()) {
      setNotice({ type: "error", text: "Write an editorial note before returning the story." });
      return;
    }
    if (!window.confirm("Send this feedback and return the story to the writer?")) return;
    setBusy(true);
    setNotice(null);
    try {
      const reviewResponse = await apiFetch(apiUrl(`/api/articles/${selectedArticle.id}/reviews`), {
        method: "POST",
        body: JSON.stringify({ content: feedback.trim() }),
      });
      if (!reviewResponse.ok) throw new Error(await apiErrorMessage(reviewResponse, "The editorial note could not be sent."));

      const statusResponse = await apiFetch(apiUrl(`/api/articles/${selectedArticle.id}`), {
        method: "PUT",
        body: JSON.stringify({ status: "REJECTED" }),
      });
      if (!statusResponse.ok) throw new Error(await apiErrorMessage(statusResponse, "The story could not be returned."));
      const updated: Article = await statusResponse.json();
      setArticles((current) => current.map((article) => article.id === updated.id ? updated : article));
      setSelectedArticle(updated);
      setFeedback("");
      await Promise.all([loadReviews(updated.id), loadQueue(false)]);
      setNotice({ type: "success", text: "The story was returned with your editorial feedback." });
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "The story could not be returned." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="editor-desk">
      <header className="editor-heading">
        <div>
          <p className="eyebrow">Editorial operations</p>
          <h2>Review board & publication queue</h2>
          <p>Review, revise, schedule, publish, return, and manage front-page placement.</p>
        </div>
        <button className="trb-btn-pill" onClick={() => void loadQueue()} disabled={loading || busy}>Refresh queue</button>
      </header>

      {notice && <div className={`crud-notice ${notice.type}`} role="status">{notice.text}</div>}

      <section className="editor-metrics" aria-label="Editorial queue totals">
        {(["SUBMITTED", "DRAFT", "REJECTED", "PUBLISHED"] as ArticleStatus[]).map((status) => (
          <button key={status} onClick={() => setStatusFilter(status)} aria-pressed={statusFilter === status}>
            <strong>{counts[status]}</strong><span>{status}</span>
          </button>
        ))}
      </section>

      <div className="editor-toolbar">
        <div className="editor-status-tabs" role="group" aria-label="Filter stories by status">
          {STATUS_OPTIONS.map((status) => (
            <button key={status} onClick={() => setStatusFilter(status)} aria-pressed={statusFilter === status}>
              {status} <span>{counts[status]}</span>
            </button>
          ))}
        </div>
        <label className="editor-search">
          <span>Search queue</span>
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Headline, author, category…" />
        </label>
      </div>

      <div className="editor-workspace">
        <aside className="editor-queue" aria-label="Article queue">
          <div className="editor-queue-heading">
            <strong>{visibleArticles.length} {visibleArticles.length === 1 ? "story" : "stories"}</strong>
            <span>{statusFilter === "ALL" ? "All records" : statusFilter}</span>
          </div>
          {loading ? (
            <p className="editor-empty">Retrieving the editorial ledger…</p>
          ) : visibleArticles.length === 0 ? (
            <p className="editor-empty">No stories match this filter.</p>
          ) : (
            <div className="editor-queue-list">
              {visibleArticles.map((article) => (
                <button
                  key={article.id}
                  className={selectedArticle?.id === article.id ? "is-selected" : ""}
                  onClick={() => selectArticle(article)}
                >
                  <span className="editor-queue-meta">
                    <span className="status-pill" style={{ borderColor: STATUS_COLOR[article.status], color: STATUS_COLOR[article.status] }}>{article.status}</span>
                    <span>{article.category}</span>
                  </span>
                  <strong>{article.title}</strong>
                  <span className="editor-queue-byline">By {article.author.username} · Updated {formatDate(article.updated_at)}</span>
                  {(article.is_pinned || article.is_breaking) && (
                    <span className="editor-flags">{article.is_pinned ? "Lead story" : ""}{article.is_pinned && article.is_breaking ? " · " : ""}{article.is_breaking ? "Breaking" : ""}</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </aside>

        <main className="editor-proof">
          {!selectedArticle ? (
            <div className="editor-empty-proof">
              <p className="eyebrow">Proof desk</p>
              <h3>Select a story</h3>
              <p>Choose any draft, submitted story, returned copy, or published article to open the complete editorial controls.</p>
            </div>
          ) : (
            <>
              <div className="editor-proof-header">
                <div>
                  <span className="status-pill" style={{ borderColor: STATUS_COLOR[selectedArticle.status], color: STATUS_COLOR[selectedArticle.status] }}>{selectedArticle.status}</span>
                  <span>Story #{selectedArticle.id}</span>
                </div>
                <div className="editor-actions">
                  <button onClick={openEditor} disabled={busy || editing}>Edit story</button>
                  {selectedArticle.status !== "PUBLISHED" && <button className="publish" onClick={() => void changeStatus("PUBLISHED")} disabled={busy}>Publish now</button>}
                  {(selectedArticle.status === "DRAFT" || selectedArticle.status === "REJECTED") && <button onClick={() => void changeStatus("SUBMITTED")} disabled={busy}>Move to review</button>}
                  {selectedArticle.status !== "DRAFT" && <button onClick={() => void changeStatus("DRAFT")} disabled={busy}>{selectedArticle.status === "PUBLISHED" ? "Unpublish" : "Move to draft"}</button>}
                  {selectedArticle.status === "PUBLISHED" && selectedArticle.slug && <a href={siteUrl(`/articles/${selectedArticle.slug}`)} target="_blank" rel="noreferrer">View live ↗</a>}
                </div>
              </div>

              {editing && editorForm ? (
                <form className="editor-edit-form" onSubmit={saveEdits}>
                  <div className="editor-edit-title"><h3>Edit article copy</h3><button type="button" onClick={() => setEditing(false)}>Close editor</button></div>
                  <label className="editor-wide">Headline<input required minLength={5} maxLength={220} value={editorForm.title} onChange={(event) => setEditorForm({ ...editorForm, title: event.target.value })} /></label>
                  <label className="editor-wide">Summary<textarea required minLength={10} maxLength={800} rows={3} value={editorForm.summary} onChange={(event) => setEditorForm({ ...editorForm, summary: event.target.value })} /></label>
                  <label>Category<input required minLength={2} maxLength={80} value={editorForm.category} onChange={(event) => setEditorForm({ ...editorForm, category: event.target.value })} /></label>
                  <label>Tags<input maxLength={500} value={editorForm.tags} onChange={(event) => setEditorForm({ ...editorForm, tags: event.target.value })} /></label>
                  <label className="editor-wide">Cover image URL<input type="url" value={editorForm.image_url} onChange={(event) => setEditorForm({ ...editorForm, image_url: event.target.value })} /></label>
                  <label className="editor-wide">Image caption<input maxLength={300} disabled={!editorForm.image_url.trim()} value={editorForm.image_caption} onChange={(event) => setEditorForm({ ...editorForm, image_caption: event.target.value })} /></label>
                  <label className="editor-check"><input type="checkbox" checked={editorForm.is_pinned} onChange={(event) => setEditorForm({ ...editorForm, is_pinned: event.target.checked })} /> Lead story / front-page placement</label>
                  <label className="editor-check"><input type="checkbox" checked={editorForm.is_breaking} onChange={(event) => setEditorForm({ ...editorForm, is_breaking: event.target.checked })} /> Breaking-news treatment</label>
                  <div className="editor-wide"><span className="editor-field-label">Article body</span><RichTextEditor value={editorForm.content} onChange={(content) => setEditorForm((current) => current ? { ...current, content } : current)} placeholder="Edit the article body…" /></div>
                  <div className="editor-form-actions editor-wide"><button className="trb-btn-solid" disabled={busy}>{busy ? "Saving…" : "Save editorial changes"}</button><button type="button" className="trb-btn-pill" onClick={() => setEditing(false)} disabled={busy}>Cancel</button></div>
                </form>
              ) : (
                <article className="editor-proof-copy">
                  <p className="eyebrow">Editorial proof · {selectedArticle.category}</p>
                  <h1>{selectedArticle.title}</h1>
                  <div className="editor-story-meta">
                    <span>By {selectedArticle.author.username}</span><span>Created {formatDate(selectedArticle.created_at)}</span><span>Updated {formatDate(selectedArticle.updated_at)}</span>
                    {selectedArticle.editor && <span>Editor {selectedArticle.editor.username}</span>}
                  </div>
                  <p className="editor-summary">{selectedArticle.summary || "No summary supplied."}</p>
                  {selectedArticle.image_url && (
                    <figure className="editor-cover">
                      <Image src={selectedArticle.image_url} alt={selectedArticle.image_caption || "Article cover"} width={1200} height={675} unoptimized />
                      {selectedArticle.image_caption && <figcaption>{selectedArticle.image_caption}</figcaption>}
                    </figure>
                  )}
                  {selectedArticle.tags && <p className="editor-tags">Tags: {selectedArticle.tags}</p>}
                  <div className="editor-body" dangerouslySetInnerHTML={{ __html: selectedArticle.content }} />
                  <div className="editor-publication-meta">
                    <span>{selectedArticle.view_count} views</span><span>Published {formatDate(selectedArticle.published_at)}</span><span>{selectedArticle.is_pinned ? "Lead story" : "Standard placement"}</span><span>{selectedArticle.is_breaking ? "Breaking news" : "Standard story"}</span>
                  </div>
                </article>
              )}

              <section className="editor-review-log">
                <div className="editor-review-heading"><div><p className="eyebrow">Internal audit log</p><h3>Editorial notes</h3></div><span>{reviews.length} {reviews.length === 1 ? "entry" : "entries"}</span></div>
                <div className="editor-review-list">
                  {reviews.length === 0 ? <p className="editor-empty">No editorial notes have been recorded.</p> : reviews.map((review) => (
                    <article key={review.id}>
                      <header><strong>{review.author.username}</strong><span>{review.author.role.replace("_", " ")} · {formatDate(review.created_at)}</span></header>
                      <p>{review.content}</p>
                    </article>
                  ))}
                </div>
                <form onSubmit={sendNote} className="editor-note-form">
                  <label htmlFor="editor-feedback">Feedback for the writer</label>
                  <textarea id="editor-feedback" value={feedback} onChange={(event) => setFeedback(event.target.value)} maxLength={4000} rows={4} placeholder="Corrections, fact-check requests, headline guidance, or return rationale…" disabled={busy} />
                  <div>
                    <button className="trb-btn-solid" disabled={busy || !feedback.trim()}>{busy ? "Working…" : "Send note"}</button>
                    {(selectedArticle.status === "DRAFT" || selectedArticle.status === "SUBMITTED") && <button type="button" className="editor-reject" onClick={() => void rejectWithFeedback()} disabled={busy || !feedback.trim()}>Return with feedback</button>}
                  </div>
                </form>
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
