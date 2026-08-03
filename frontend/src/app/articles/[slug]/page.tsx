"use client";

import { useCallback, useEffect, use } from "react";
import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { apiFetch } from "../../../lib/auth";
import { apiUrl } from "../../../lib/config";
import Header from "../../components/Header";

interface User {
  id: number;
  username: string;
  role: string;
}

interface Comment {
  id: number;
  content: string;
  created_at: string;
  author: {
    id: number;
    username: string;
    role: string;
  };
}

interface Article {
  id: number;
  title: string;
  content: string;
  summary: string;
  category: string;
  image_url?: string;
  image_caption?: string;
  tags?: string;
  view_count?: number;
  created_at: string;
  published_at?: string;
  author: {
    username: string;
  };
  editor?: {
    username: string;
  };
}

function formatDate(dateStr?: string) {
  if (!dateStr) return "N/A";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getContentHtml(content: string) {
  if (!content) return "";
  if (content.trim().startsWith("<")) {
    return content;
  }
  return content
    .split("\n\n")
    .map((para) => `<p>${escapeHtml(para)}</p>`)
    .join("");
}

export default function ArticleDetail({ params }: { params: Promise<{ slug: string }> }) {
  const resolvedParams = use(params);
  const articleSlug = resolvedParams.slug;

  const [article, setArticle] = useState<Article | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [commentLoading, setCommentLoading] = useState(false);
  const [commentError, setCommentError] = useState("");
  const [commentsEnabled, setCommentsEnabled] = useState(true);
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
  const [editingCommentText, setEditingCommentText] = useState("");

  const fetchArticle = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(apiUrl(`/api/articles/${articleSlug}`));
      if (res.ok) {
        setArticle(await res.json());
      } else {
        setArticle(null);
      }
    } catch (err) {
      console.error("Failed to load article:", err);
      setArticle(null);
    } finally {
      setLoading(false);
    }
  }, [articleSlug]);

  const fetchComments = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/articles/${articleSlug}/comments`));
      if (res.ok) {
        setComments(await res.json());
      }
    } catch (err) {
      console.error("Failed to load comments:", err);
    }
  }, [articleSlug]);

  const fetchUser = useCallback(async () => {
    try {
      const res = await apiFetch(apiUrl("/api/auth/me"));
      if (res.ok) {
        setUser(await res.json());
      }
    } catch (err) {
      console.error("Failed to load current user:", err);
    }
  }, []);

  const fetchCommentSetting = useCallback(async () => {
    try {
      const response = await fetch(apiUrl("/api/settings"));
      if (!response.ok) return;
      const data = await response.json();
      if (data?.features?.comments_enabled !== undefined) {
        const value = data.features.comments_enabled;
        setCommentsEnabled(value === true || String(value).toLowerCase() === "true");
      }
    } catch {
      // Use the open-by-default setting when configuration is unavailable.
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      fetchArticle();
      fetchComments();
      fetchUser();
      fetchCommentSetting();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchArticle, fetchComments, fetchUser, fetchCommentSetting]);

  const handlePostComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    setCommentLoading(true);
    setCommentError("");
    try {
      const res = await apiFetch(apiUrl(`/api/articles/${articleSlug}/comments`), {
        method: "POST",
        body: JSON.stringify({ content: newComment.trim() }),
      });

      if (res.ok) {
        setNewComment("");
        fetchComments();
      } else {
        const data = await res.json().catch(() => null);
        setCommentError(data?.detail || "Failed to submit response. Please log in again and retry.");
      }
    } catch (err) {
      console.error("Failed to post comment:", err);
      setCommentError("Connection error while submitting your response.");
    } finally {
      setCommentLoading(false);
    }
  };

  const handleEditComment = async (commentId: number) => {
    if (!editingCommentText.trim()) return;
    setCommentError("");
    const response = await apiFetch(apiUrl(`/api/articles/${articleSlug}/comments/${commentId}`), {
      method: "PUT",
      body: JSON.stringify({ content: editingCommentText.trim() }),
    });
    if (response.ok) {
      setEditingCommentId(null);
      setEditingCommentText("");
      fetchComments();
    } else {
      setCommentError(await response.json().then((data) => data.detail).catch(() => "Could not edit response."));
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!window.confirm("Delete this response from the public record?")) return;
    const response = await apiFetch(apiUrl(`/api/articles/${articleSlug}/comments/${commentId}`), { method: "DELETE" });
    if (response.ok) fetchComments();
    else setCommentError(await response.json().then((data) => data.detail).catch(() => "Could not delete response."));
  };

  if (loading) {
    return (
      <div className="trb-container" style={{ minHeight: "80vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center", fontFamily: "var(--font-mono)", fontSize: "0.85rem", letterSpacing: "2px", textTransform: "uppercase" }}>
          📜 RETRIEVING FULL BROADSIDE DISPATCH PROOF...
        </div>
      </div>
    );
  }

  if (!article) {
    return (
      <div className="trb-container" style={{ paddingTop: "5rem" }}>
        <div style={{ maxWidth: "600px", margin: "0 auto", padding: "3rem 2rem", border: "4px double var(--border-color)", backgroundColor: "var(--card-bg)", textAlign: "center" }}>
          <h2 style={{ fontFamily: "var(--font-headline)", fontSize: "2rem", textTransform: "uppercase", marginBottom: "0.5rem" }}>Dispatch Not Found</h2>
          <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", opacity: 0.8, marginBottom: "1.5rem" }}>
            This chronicle has been lost in the pressroom archives or was never approved for public publication.
          </p>
          <Link href="/" className="trb-btn-solid" style={{ textDecoration: "none" }}>
            RETURN TO FRONT PAGE
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="trb-container">
      <Header />

      <div style={{ marginBottom: "1.5rem" }}>
        <Link href="/" className="trb-btn-pill" style={{ textDecoration: "none" }}>
          ← RETURN TO FRONT PAGE
        </Link>
      </div>

      {/* Main Reading Article */}
      <article id="main-content" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <header style={{ borderBottom: "3px double var(--border-color)", paddingBottom: "1.25rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--accent-red)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px", marginBottom: "0.5rem" }}>
            <span className="trb-badge-red">{article.category}</span>
            <span>•</span>
            <span>{formatDate(article.published_at || article.created_at)}</span>
          </div>

          <h1 style={{ fontFamily: "var(--font-headline)", fontSize: "clamp(2.2rem, 5vw, 3.8rem)", fontWeight: 900, textTransform: "uppercase", lineHeight: 1.05, margin: "0.5rem 0" }}>
            {article.title}
          </h1>

          {article.summary && (
            <p style={{ fontFamily: "var(--font-headline)", fontStyle: "italic", fontSize: "1.25rem", lineHeight: 1.5, opacity: 0.9, marginBottom: "1rem" }}>
              {article.summary}
            </p>
          )}

          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", borderTop: "2px double var(--border-color)", borderBottom: "2px double var(--border-color)", padding: "0.5rem 0", fontFamily: "var(--font-mono)", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", gap: "0.75rem" }}>
            <div>SCRIBE: <strong>{article.author.username.toUpperCase()}</strong></div>
            <div>VIEWS: {article.view_count || 0} READS</div>
            {article.editor && <div>EDITOR: {article.editor.username.toUpperCase()}</div>}
            <button type="button" onClick={() => window.print()} className="trb-btn-pill">
              🖨️ PRINT ARTICLE
            </button>
          </div>
        </header>

        {article.image_url && (
          <div className="trb-lead-image-box">
            <Image src={article.image_url} alt={article.title} className="trb-lead-image" width={1100} height={620} priority style={{ height: "420px" }} />
            {article.image_caption && <p className="article-image-caption">{article.image_caption}</p>}
          </div>
        )}

        <div
          className="trb-dropcap"
          style={{ borderBottom: "3px double var(--border-color)", paddingBottom: "2.5rem", marginTop: "1rem" }}
          dangerouslySetInnerHTML={{ __html: getContentHtml(article.content) }}
        />
      </article>

      {/* Public Comments / Responses */}
      <section style={{ marginTop: "3rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "3px double var(--border-color)", paddingBottom: "0.5rem", marginBottom: "1.5rem" }}>
          <h3 style={{ fontFamily: "var(--font-headline)", fontSize: "1.6rem", fontWeight: 900, textTransform: "uppercase" }}>
            Reader Responses & Public Record
          </h3>
          <span className="trb-badge-red" style={{ backgroundColor: "var(--fg-ink)" }}>
            {comments.length} FILED
          </span>
        </div>

        {/* Comment Form */}
        <div className="trb-sidebar-card" style={{ marginBottom: "2rem" }}>
          {!commentsEnabled ? (
            <p style={{ textAlign: "center", padding: "1.5rem", fontFamily: "var(--font-mono)", fontSize: ".8rem", fontWeight: 700 }}>
              Reader responses are closed for this edition.
            </p>
          ) : user ? (
            <form onSubmit={handlePostComment} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700 }}>
                Write your public response as <strong>{user.username}</strong> ({user.role}):
              </label>
              <textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Submit your thoughts for the public broadside record..."
                className="trb-input"
                style={{ width: "100%", height: "100px", resize: "vertical" }}
                disabled={commentLoading}
                required
              />
              {commentError && (
                <p style={{ color: "var(--accent-red)", fontFamily: "var(--font-mono)", fontSize: "0.75rem", fontWeight: 700 }}>
                  ⚠️ {commentError}
                </p>
              )}
              <div>
                <button type="submit" className="trb-btn-solid" disabled={commentLoading}>
                  {commentLoading ? "PUBLISHING..." : "POST RESPONSE TO RECORD"}
                </button>
              </div>
            </form>
          ) : (
            <div style={{ textAlign: "center", padding: "1.5rem" }}>
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 700, marginBottom: "1rem" }}>
                YOU MUST BE SIGNED IN TO POST A PUBLIC RESPONSE
              </p>
              <Link href="/login" className="trb-btn-solid" style={{ textDecoration: "none" }}>
                SIGN IN WITH PRESS CREDENTIALS
              </Link>
            </div>
          )}
        </div>

        {/* Comment List */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {comments.length === 0 ? (
            <p style={{ fontFamily: "var(--font-mono)", fontStyle: "italic", opacity: 0.7, textAlign: "center", padding: "2rem" }}>
              No public responses recorded yet. Be the first to express your thoughts.
            </p>
          ) : (
            comments.map((comment) => (
              <div key={comment.id} style={{ border: "1px solid var(--border-color)", padding: "1rem 1.25rem", backgroundColor: "var(--card-bg)", borderRadius: "3px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "var(--font-mono)", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.35rem", marginBottom: "0.6rem" }}>
                  <span>RESPONDENT: <strong>{comment.author.username.toUpperCase()}</strong> ({comment.author.role})</span>
                  <span>{formatDate(comment.created_at)}</span>
                </div>
                {editingCommentId === comment.id ? (
                  <div className="comment-edit-form">
                    <textarea value={editingCommentText} onChange={(event) => setEditingCommentText(event.target.value)} maxLength={2000} />
                    <button className="trb-btn-solid" onClick={() => handleEditComment(comment.id)}>Save</button>
                    <button className="trb-btn-pill" onClick={() => setEditingCommentId(null)}>Cancel</button>
                  </div>
                ) : (
                  <p style={{ fontSize: "0.95rem", lineHeight: 1.6 }}>{comment.content}</p>
                )}
                {user && (user.id === comment.author.id || ["ADMIN", "SUPER_ADMIN"].includes(user.role)) && editingCommentId !== comment.id && (
                  <div className="comment-actions">
                    <button onClick={() => { setEditingCommentId(comment.id); setEditingCommentText(comment.content); }}>Edit</button>
                    <button className="danger" onClick={() => handleDeleteComment(comment.id)}>Delete</button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
