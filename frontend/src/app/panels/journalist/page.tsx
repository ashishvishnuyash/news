"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import RichTextEditor from "../../components/RichTextEditor";
import { apiErrorMessage, apiFetch } from "../../../lib/auth";
import { apiUrl, siteUrl } from "../../../lib/config";

interface Article {
  id: number;
  title: string;
  slug: string;
  content: string;
  summary: string;
  category: string;
  image_url?: string;
  image_caption?: string;
  tags?: string;
  status: string;
  view_count: number;
  created_at: string;
  published_at?: string;
}

interface ReviewComment {
  id: number;
  content: string;
  created_at: string;
  author: { username: string; role: string };
}

interface Notification {
  id: number;
  message: string;
  type: string;
  is_read: boolean;
  created_at: string;
}

const CATEGORIES = ["Technology", "Opinion", "Science", "Sports", "Global", "Politics", "Culture", "Business"];

const STATUS_BADGE: Record<string, { bg: string; label: string }> = {
  DRAFT: { bg: "gray", label: "DRAFT" },
  SUBMITTED: { bg: "navy", label: "IN REVIEW" },
  PUBLISHED: { bg: "darkgreen", label: "PUBLISHED" },
  REJECTED: { bg: "var(--accent-red)", label: "RETURNED" },
};

export default function JournalistDashboard() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showNotifs, setShowNotifs] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  // Form state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [summary, setSummary] = useState("");
  const [category, setCategory] = useState("Technology");
  const [imageUrl, setImageUrl] = useState("");
  const [imageCaption, setImageCaption] = useState("");
  const [imageUploading, setImageUploading] = useState(false);
  const [imageUploadError, setImageUploadError] = useState("");
  const [tags, setTags] = useState("");

  // Reviews
  const [reviews, setReviews] = useState<ReviewComment[]>([]);
  const [showReviewsId, setShowReviewsId] = useState<number | null>(null);
  const [reviewText, setReviewText] = useState("");

  const wordCount = content
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .filter(Boolean).length;

  useEffect(() => {
    const timer = window.setTimeout(() => {
      fetchMyArticles();
      fetchNotifications();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function fetchMyArticles() {
    setLoading(true);
    try {
      const res = await apiFetch(apiUrl("/api/articles/journalist/my"));
      if (res.ok) setArticles(await res.json());
      else console.error("Failed to fetch articles:", res.status);
    } catch (err) {
      console.error("Network error:", err);
    } finally {
      setLoading(false);
    }
  }

  async function fetchNotifications() {
    try {
      const res = await apiFetch(apiUrl("/api/users/me/notifications"));
      if (res.ok) setNotifications(await res.json());
    } catch (err) { console.error(err); }
  }

  const handleMarkAllRead = async () => {
    try {
      await apiFetch(apiUrl("/api/users/me/notifications/read-all"), { method: "PUT" });
      fetchNotifications();
    } catch (err) { console.error(err); }
  };

  const handleSaveDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    if (imageUploading) {
      alert("Please wait for the image upload to finish before saving your draft.");
      return;
    }
    const isContentEmpty = !content.trim() || content === "<p><br></p>";
    if (!title.trim() || isContentEmpty || summary.trim().length < 10) {
      alert("Headline, dispatch content, and a summary of at least 10 characters are required.");
      return;
    }

    try {
      const isEdit = editingId !== null;
      const url = isEdit
        ? apiUrl(`/api/articles/${editingId}`)
        : apiUrl("/api/articles");
      const method = isEdit ? "PUT" : "POST";

      const payload = {
        title,
        content,
        summary: summary.trim(),
        category,
        image_url: imageUrl.trim() || null,
        image_caption: imageUrl.trim() ? imageCaption.trim() || null : null,
        tags: tags || undefined,
        status: "DRAFT",
      };

      const res = await apiFetch(url, { method, body: JSON.stringify(payload) });

      if (res.ok) {
        resetForm();
        fetchMyArticles();
        alert(isEdit ? "Draft updated successfully!" : "New draft saved to the archive!");
      } else {
        alert(await apiErrorMessage(res, "Failed to save draft."));
      }
    } catch (err) {
      console.error(err);
      alert("Could not reach the newsroom server. Check your connection and try again.");
    }
  };

  const handleSubmitForReview = async (artId: number) => {
    if (!confirm("Submit this dispatch to the editorial queue? You will not be able to edit it until the editors review it.")) return;
    try {
      const res = await apiFetch(apiUrl(`/api/articles/${artId}`), {
        method: "PUT",
        body: JSON.stringify({ status: "SUBMITTED" }),
      });
      if (res.ok) {
        fetchMyArticles();
        if (editingId === artId) resetForm();
        alert("Dispatch submitted to the editorial queue!");
      } else {
        alert("Failed to submit dispatch.");
      }
    } catch (err) { console.error(err); }
  };

  const handleDeleteDraft = async (artId: number, artTitle: string) => {
    if (!confirm(`Delete draft "${artTitle}"? This cannot be undone.`)) return;
    try {
      const res = await apiFetch(apiUrl(`/api/articles/${artId}`), { method: "DELETE" });
      if (res.ok) {
        if (editingId === artId) resetForm();
        fetchMyArticles();
        alert("Draft deleted.");
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to delete draft.");
      }
    } catch (err) { console.error(err); }
  };

  const handleEditSelect = (art: Article) => {
    setEditingId(art.id);
    setTitle(art.title);
    setContent(art.content);
    setSummary(art.summary || "");
    setCategory(art.category);
    setImageUrl(art.image_url || "");
    setImageCaption(art.image_caption || "");
    setTags(art.tags || "");
    setShowReviewsId(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    const maximumBytes = 8 * 1024 * 1024;
    if (file.size > maximumBytes) {
      setImageUploadError("Choose an image no larger than 8 MB.");
      return;
    }

    setImageUploading(true);
    setImageUploadError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await apiFetch(apiUrl("/api/media/images"), {
        method: "POST",
        body: formData,
      });
      const result = await response.json().catch(() => null);
      if (!response.ok || typeof result?.url !== "string") {
        throw new Error(result?.detail || "The image could not be uploaded.");
      }
      setImageUrl(result.url);
    } catch (error) {
      setImageUploadError(error instanceof Error ? error.message : "The image could not be uploaded.");
    } finally {
      setImageUploading(false);
    }
  };

  const fetchReviews = async (artId: number) => {
    try {
      const res = await apiFetch(apiUrl(`/api/articles/${artId}/reviews`));
      if (res.ok) {
        setReviews(await res.json());
        setShowReviewsId(artId);
      }
    } catch (err) { console.error(err); }
  };

  const handlePostReviewComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewText.trim() || !showReviewsId) return;
    try {
      const res = await apiFetch(apiUrl(`/api/articles/${showReviewsId}/reviews`), {
        method: "POST",
        body: JSON.stringify({ content: reviewText }),
      });
      if (res.ok) { setReviewText(""); fetchReviews(showReviewsId); }
    } catch (err) { console.error(err); }
  };

  const resetForm = () => {
    setEditingId(null);
    setTitle("");
    setContent("");
    setSummary("");
    setCategory("Technology");
    setImageUrl("");
    setImageCaption("");
    setImageUploadError("");
    setTags("");
    setShowReviewsId(null);
    setReviews([]);
    setShowPreview(false);
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="journalist-dashboard" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div className="journalist-desk-header" style={{ borderBottom: "3px double var(--border-color)", paddingBottom: "1rem", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <span className="trb-badge-red" style={{ backgroundColor: "darkgreen" }}>
            ✒️ PRESS CORRESPONDENT DESK
          </span>
          <h1 style={{ fontFamily: "var(--font-headline)", fontSize: "2.2rem", fontWeight: 900, textTransform: "uppercase", margin: "0.4rem 0 0" }}>
            CORRESPONDENT WORKSPACE
          </h1>
        </div>

        {/* Notifications Bell */}
        <div style={{ position: "relative" }}>
          <button
            onClick={() => setShowNotifs(!showNotifs)}
            className="trb-btn-pill"
            style={{ padding: "0.5rem 0.85rem", fontSize: "0.8rem" }}
          >
            🔔 NOTICES {unreadCount > 0 && (
              <span className="trb-badge-red" style={{ marginLeft: "0.4rem" }}>
                {unreadCount}
              </span>
            )}
          </button>
          {showNotifs && (
            <div className="journalist-notice-menu" style={{
              position: "absolute",
              right: 0,
              top: "calc(100% + 0.5rem)",
              width: "340px",
              background: "var(--bg-paper)",
              border: "2px solid var(--border-color)",
              boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
              borderRadius: "3px",
              zIndex: 999,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "0.75rem 1rem", borderBottom: "1px solid var(--border-color)" }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", fontWeight: "bold" }}>EDITORIAL NOTICES</span>
                <button onClick={handleMarkAllRead} style={{ background: "none", border: "none", fontSize: "0.72rem", fontFamily: "var(--font-mono)", cursor: "pointer", color: "var(--accent-red)" }}>
                  MARK ALL READ
                </button>
              </div>
              <div style={{ maxHeight: "280px", overflowY: "auto" }}>
                {notifications.length === 0 ? (
                  <p style={{ padding: "1rem", fontFamily: "var(--font-mono)", fontSize: "0.8rem", opacity: 0.7, textAlign: "center" }}>No notices yet.</p>
                ) : notifications.map(n => (
                  <div
                    key={n.id}
                    style={{
                      padding: "0.75rem 1rem",
                      borderBottom: "1px solid var(--border-color)",
                      background: n.is_read ? "transparent" : "var(--card-bg)",
                    }}
                  >
                    <p style={{ fontSize: "0.82rem", marginBottom: "0.2rem" }}>{n.message}</p>
                    <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", opacity: 0.7 }}>
                      {new Date(n.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Article Form Card */}
      <section className="trb-sidebar-card journalist-composer" style={{ padding: "1.75rem" }}>
        <h2 style={{ fontFamily: "var(--font-headline)", fontSize: "1.5rem", fontWeight: 900, textTransform: "uppercase", marginBottom: "1.25rem" }}>
          {editingId ? `EDITING DISPATCH #${editingId}` : "FILE NEW DISPATCH"}
        </h2>

        <form onSubmit={handleSaveDraft} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }} htmlFor="headline">
                Dispatch Headline *
              </label>
              <input
                id="headline"
                type="text"
                className="trb-input"
                style={{ width: "100%", fontSize: "1.1rem", fontFamily: "var(--font-headline)", fontWeight: 700 }}
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Enter your article headline..."
                required
              />
            </div>

            <div className="journalist-form-row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              <div>
                <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }} htmlFor="category">Category</label>
                <select
                  id="category"
                  className="trb-select"
                  style={{ width: "100%" }}
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                >
                  {CATEGORIES.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }} htmlFor="tags">Tags (comma-separated)</label>
                <input
                  id="tags"
                  type="text"
                  className="trb-input"
                  style={{ width: "100%" }}
                  value={tags}
                  onChange={e => setTags(e.target.value)}
                  placeholder="e.g. politics, economy, analysis"
                />
              </div>
            </div>

            <div className="journalist-image-field">
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }} htmlFor="image-file">Cover Image (optional)</label>
              <div className="journalist-image-upload">
                <input
                  id="image-file"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="sr-only"
                  onChange={handleImageUpload}
                  disabled={imageUploading}
                />
                <label htmlFor="image-file" className="trb-btn-pill journalist-upload-button" aria-disabled={imageUploading}>
                  {imageUploading ? "UPLOADING PHOTO…" : "UPLOAD A PHOTO"}
                </label>
                <span>{imageUrl ? "Image ready to publish" : "JPEG, PNG, or WebP · up to 8 MB"}</span>
              </div>
              {imageUploadError && <p className="journalist-upload-error" role="alert">{imageUploadError}</p>}
              <label className="journalist-url-label" style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.7rem", textTransform: "uppercase", fontWeight: 700 }} htmlFor="image-url">Or use an image URL</label>
              <input
                id="image-url"
                type="url"
                className="trb-input"
                style={{ width: "100%" }}
                value={imageUrl}
                onChange={e => setImageUrl(e.target.value)}
                placeholder="https://example.com/image.jpg"
              />
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, margin: "0.75rem 0 0.35rem" }} htmlFor="image-caption">
                Image Caption {imageUrl ? "(optional)" : "(add an image first)"}
              </label>
              <input
                id="image-caption"
                type="text"
                value={imageCaption}
                onChange={e => setImageCaption(e.target.value)}
                disabled={!imageUrl.trim()}
                maxLength={300}
                className="trb-input"
                style={{ width: "100%" }}
                placeholder="Describe the photograph and credit its source..."
              />
            </div>

            <div>
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }} htmlFor="summary">Article Summary *</label>
              <textarea
                id="summary"
                className="trb-input"
                style={{ width: "100%", resize: "vertical" }}
                value={summary}
                onChange={e => setSummary(e.target.value)}
                rows={2}
                minLength={10}
                maxLength={800}
                required
                placeholder="Write a brief summary for the front page..."
              />
            </div>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700 }} htmlFor="dispatch-content">
                Dispatch Content *
              </label>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", fontWeight: 700, opacity: 0.8 }}>
                {wordCount} WORDS
              </span>
            </div>
            <RichTextEditor
              value={content}
              onChange={setContent}
              placeholder="Type your chronicle here. Use the toolbar for headers, styling, and lists..."
            />
          </div>

          <div className="journalist-form-actions" style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <button type="submit" className="trb-btn-solid" disabled={imageUploading}>
              {editingId ? "SAVE UPDATED DRAFT" : "SAVE NEW DRAFT"}
            </button>

            <button
              type="button"
              className="trb-btn-pill"
              onClick={() => setShowPreview(!showPreview)}
              disabled={!title && !content}
            >
              {showPreview ? "HIDE PROOF PREVIEW" : "PROOF PREVIEW"}
            </button>

            {editingId && (
              <button
                type="button"
                className="trb-btn-pill"
                onClick={() => handleSubmitForReview(editingId)}
                style={{ borderColor: "navy", color: "navy" }}
              >
                SUBMIT FOR EDITORIAL REVIEW
              </button>
            )}

            <button type="button" className="trb-btn-pill" onClick={resetForm}>
              CLEAR DESK
            </button>
          </div>
        </form>

        {/* Preview Panel */}
        {showPreview && (
          <div className="journalist-preview" style={{ marginTop: "2rem", border: "4px double var(--border-color)", padding: "2rem", backgroundColor: "var(--bg-paper)", borderRadius: "3px" }}>
            <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", marginBottom: "1rem", opacity: 0.7 }}>
              ─── BROADSIDE PROOF PREVIEW ───
            </p>
            {imageUrl && (
              <Image
                src={imageUrl}
                alt="Cover"
                width={1000}
                height={500}
                style={{ width: "100%", maxHeight: "280px", objectFit: "cover", marginBottom: "1.5rem", filter: "grayscale(100%) contrast(1.2)", border: "1px solid var(--border-color)" }}
              />
            )}
            {imageUrl && imageCaption && <p className="article-image-caption">{imageCaption}</p>}
            <h2 style={{ fontFamily: "var(--font-headline)", fontSize: "2.2rem", textTransform: "uppercase", fontWeight: 900, marginBottom: "0.5rem" }}>{title || "Untitled Dispatch"}</h2>
            <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", marginBottom: "1.5rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.5rem" }}>
              CATEGORY: {category.toUpperCase()} · {wordCount} WORDS
            </p>
            <div
              style={{ fontSize: "1rem", lineHeight: 1.7 }}
              dangerouslySetInnerHTML={{ __html: content }}
            />
          </div>
        )}

        {/* Editorial Review Log */}
        {showReviewsId && (
          <div className="journalist-feedback" style={{ marginTop: "2rem", border: "2px double var(--border-color)", padding: "1.5rem", borderRadius: "3px" }}>
            <h4 style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 800, textTransform: "uppercase", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.4rem", marginBottom: "1rem" }}>
              EDITORIAL FEEDBACK LOG — DISPATCH #{showReviewsId}
            </h4>
            <div style={{ maxHeight: "200px", overflowY: "auto", marginBottom: "1rem" }}>
              {reviews.length === 0 ? (
                <p style={{ fontStyle: "italic", fontSize: "0.85rem", opacity: 0.7 }}>No editorial feedback logged yet.</p>
              ) : reviews.map(rev => (
                <div key={rev.id} style={{ fontSize: "0.85rem", marginBottom: "0.75rem", paddingBottom: "0.75rem", borderBottom: "1px dashed var(--border-color)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "var(--font-mono)", fontSize: "0.72rem", opacity: 0.8, marginBottom: "0.25rem" }}>
                    <span>FROM: {rev.author.username.toUpperCase()} ({rev.author.role})</span>
                    <span>{new Date(rev.created_at).toLocaleDateString()}</span>
                  </div>
                  <p>{rev.content}</p>
                </div>
              ))}
            </div>
            <form className="journalist-feedback-form" onSubmit={handlePostReviewComment} style={{ display: "flex", gap: "0.5rem" }}>
              <input
                type="text"
                value={reviewText}
                onChange={e => setReviewText(e.target.value)}
                placeholder="Reply to editor's note..."
                className="trb-input"
                style={{ flex: 1 }}
              />
              <button type="submit" className="trb-btn-solid">SEND RESPONSE</button>
            </form>
          </div>
        )}
      </section>

      {/* Articles Archive */}
      <section className="trb-sidebar-card" style={{ padding: "1.75rem" }}>
        <div className="journalist-archive-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
          <h2 style={{ fontFamily: "var(--font-headline)", fontSize: "1.5rem", fontWeight: 900, textTransform: "uppercase" }}>
            MY FILED DISPATCHES ({articles.length})
          </h2>
          <button onClick={fetchMyArticles} className="trb-btn-solid">
            REFRESH ARCHIVE
          </button>
        </div>

        {loading ? (
          <p style={{ fontFamily: "var(--font-mono)" }}>Loading dispatches...</p>
        ) : articles.length === 0 ? (
          <p style={{ fontFamily: "var(--font-mono)", fontStyle: "italic", opacity: 0.7 }}>
            No dispatches filed yet. File your first chronicle above.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {articles.map(art => {
              const badge = STATUS_BADGE[art.status] || { bg: "var(--fg-ink)", label: art.status };
              const canEdit = art.status === "DRAFT" || art.status === "REJECTED";
              return (
                <div
                  key={art.id}
                  className="journalist-archive-item"
                  style={{
                    border: "1px solid var(--border-color)",
                    padding: "1.25rem",
                    display: "grid",
                    gridTemplateColumns: "1fr auto",
                    gap: "1rem",
                    alignItems: "start",
                    backgroundColor: "var(--bg-paper)",
                    borderRadius: "3px",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.35rem", flexWrap: "wrap" }}>
                      <span className="trb-badge-red" style={{ backgroundColor: badge.bg }}>
                        {badge.label}
                      </span>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", opacity: 0.8 }}>
                        {art.category}
                      </span>
                      {art.status === "PUBLISHED" && (
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", opacity: 0.8 }}>
                          👁 {art.view_count} views
                        </span>
                      )}
                    </div>
                    <h3 style={{ fontFamily: "var(--font-headline)", fontSize: "1.2rem", fontWeight: 800, marginBottom: "0.3rem" }}>
                      {art.title}
                    </h3>
                    <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", opacity: 0.7 }}>
                      Filed: {new Date(art.created_at).toLocaleDateString()}
                      {art.published_at && ` · Published: ${new Date(art.published_at).toLocaleDateString()}`}
                    </p>
                  </div>
                  <div className="journalist-archive-actions" style={{ display: "flex", flexDirection: "column", gap: "0.4rem", alignItems: "flex-end" }}>
                    {canEdit && (
                      <button
                        onClick={() => handleEditSelect(art)}
                        className="trb-btn-solid"
                      >
                        EDIT DRAFT
                      </button>
                    )}
                    {art.status === "DRAFT" && (
                      <button
                        onClick={() => handleSubmitForReview(art.id)}
                        className="trb-btn-pill"
                        style={{ borderColor: "navy", color: "navy" }}
                      >
                        SUBMIT FOR REVIEW
                      </button>
                    )}
                    <button
                      onClick={() => fetchReviews(art.id)}
                      className="trb-btn-pill"
                    >
                      REVIEW NOTES
                    </button>
                    {art.status === "PUBLISHED" && (
                      <a
                        href={siteUrl(`/articles/${art.slug}`)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="trb-btn-solid"
                        style={{ textDecoration: "none" }}
                      >
                        VIEW BROADSIDE ↗
                      </a>
                    )}
                    {(art.status === "DRAFT" || art.status === "REJECTED") && (
                      <button
                        onClick={() => handleDeleteDraft(art.id, art.title)}
                        className="trb-btn-pill"
                        style={{ borderColor: "var(--accent-red)", color: "var(--accent-red)" }}
                      >
                        DELETE
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
