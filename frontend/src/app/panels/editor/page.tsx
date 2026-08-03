"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../../../lib/auth";
import { apiUrl, siteUrl } from "../../../lib/config";

interface Article {
  id: number;
  title: string;
  slug: string;
  content: string;
  summary: string;
  category: string;
  status: string;
  view_count: number;
  created_at: string;
  published_at?: string;
  author: { username: string };
  editor?: { username: string } | null;
}

interface ReviewComment {
  id: number;
  content: string;
  created_at: string;
  author: { username: string; role: string };
}

const STATUS_OPTIONS = ["SUBMITTED", "PUBLISHED", "DRAFT", "REJECTED"];

const STATUS_COLOR: Record<string, string> = {
  PUBLISHED: "darkgreen",
  DRAFT: "gray",
  SUBMITTED: "navy",
  REJECTED: "var(--accent-red)",
};

export default function EditorQueue() {
  const [queue, setQueue] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [statusFilter, setStatusFilter] = useState("SUBMITTED");

  // Review
  const [reviews, setReviews] = useState<ReviewComment[]>([]);
  const [feedback, setFeedback] = useState("");
  const [submittingReview, setSubmittingReview] = useState(false);
  const [actionMsg, setActionMsg] = useState("");

  const fetchQueue = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch(
        apiUrl(`/api/articles/editor/queue?status_filter=${statusFilter}`)
      );
      if (res.ok) {
        const data = await res.json();
        setQueue(data);
      } else {
        console.error("Failed to fetch queue:", res.status);
      }
    } catch (err) {
      console.error("Network error:", err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    const timer = window.setTimeout(fetchQueue, 0);
    return () => window.clearTimeout(timer);
  }, [fetchQueue]);

  const handleSelectArticle = async (art: Article) => {
    setSelectedArticle(art);
    setFeedback("");
    setActionMsg("");
    try {
      const res = await apiFetch(apiUrl(`/api/articles/${art.id}/reviews`));
      if (res.ok) setReviews(await res.json());
    } catch (err) {
      console.error(err);
    }
  };

  const handlePublish = async (artId: number) => {
    if (!confirm("Approve and publish this dispatch to the front page?")) return;
    try {
      const res = await apiFetch(apiUrl(`/api/articles/${artId}`), {
        method: "PUT",
        body: JSON.stringify({ status: "PUBLISHED" }),
      });
      if (res.ok) {
        setActionMsg("✓ Dispatch published successfully to front page!");
        setSelectedArticle(null);
        fetchQueue();
      } else {
        setActionMsg("✗ Failed to publish. Try again.");
      }
    } catch (err) {
      console.error(err);
      setActionMsg("✗ Network error.");
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedArticle || !feedback.trim()) {
      alert("Please provide feedback before rejecting.");
      return;
    }
    setSubmittingReview(true);
    try {
      const commentRes = await apiFetch(apiUrl(`/api/articles/${selectedArticle.id}/reviews`), {
        method: "POST",
        body: JSON.stringify({ content: feedback }),
      });
      if (!commentRes.ok) throw new Error("Failed to post review comment.");

      const statusRes = await apiFetch(apiUrl(`/api/articles/${selectedArticle.id}`), {
        method: "PUT",
        body: JSON.stringify({ status: "REJECTED" }),
      });
      if (statusRes.ok) {
        setActionMsg("✓ Dispatch returned to journalist with your notes.");
        setSelectedArticle(null);
        fetchQueue();
      } else {
        setActionMsg("✗ Failed to update status.");
      }
    } catch (err) {
      console.error(err);
      setActionMsg("✗ Error during review processing.");
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleSendNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedArticle || !feedback.trim()) return;
    try {
      const res = await apiFetch(apiUrl(`/api/articles/${selectedArticle.id}/reviews`), {
        method: "POST",
        body: JSON.stringify({ content: feedback }),
      });
      if (res.ok) {
        setFeedback("");
        handleSelectArticle(selectedArticle);
        setActionMsg("✓ Note sent to journalist.");
      }
    } catch (err) { console.error(err); }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <div style={{ borderBottom: "3px double var(--border-color)", paddingBottom: "1rem" }}>
        <span className="trb-badge-red" style={{ backgroundColor: "navy" }}>
          ✍️ EDITORIAL REVIEW DESK
        </span>
        <h1 style={{ fontFamily: "var(--font-headline)", fontSize: "2.2rem", fontWeight: 900, textTransform: "uppercase", margin: "0.4rem 0 0" }}>
          EDITORIAL REVIEW BOARD & QUEUE
        </h1>
      </div>

      {actionMsg && (
        <div style={{
          border: `1px solid ${actionMsg.startsWith("✓") ? "darkgreen" : "var(--accent-red)"}`,
          color: actionMsg.startsWith("✓") ? "darkgreen" : "var(--accent-red)",
          padding: "0.75rem 1rem",
          fontFamily: "var(--font-mono)",
          fontSize: "0.85rem",
          fontWeight: 700,
          backgroundColor: "var(--card-bg)"
        }}>
          {actionMsg}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "2rem" }}>
        <div className="panel-split">
          {/* Queue List */}
          <section className="trb-sidebar-card" style={{ padding: "1.25rem" }}>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }}>
                FILTER QUEUE BY STATUS
              </label>
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className="trb-select"
                style={{ width: "100%" }}
              >
                {STATUS_OPTIONS.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <h3 style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 800 }}>
                {queue.length} DISPATCH{queue.length !== 1 ? "ES" : ""}
              </h3>
              <button onClick={fetchQueue} className="trb-btn-pill">
                REFRESH
              </button>
            </div>

            {loading ? (
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}>Retrieving queue...</p>
            ) : queue.length === 0 ? (
              <p style={{ fontStyle: "italic", fontSize: "0.9rem", opacity: 0.7 }}>
                No dispatches with status &quot;{statusFilter}&quot;.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxHeight: "600px", overflowY: "auto" }}>
                {queue.map(art => (
                  <div
                    key={art.id}
                    onClick={() => handleSelectArticle(art)}
                    style={{
                      border: selectedArticle?.id === art.id ? "2px solid var(--fg-ink)" : "1px solid var(--border-color)",
                      padding: "0.85rem",
                      cursor: "pointer",
                      background: selectedArticle?.id === art.id ? "var(--bg-paper)" : "transparent",
                      borderRadius: "3px",
                    }}
                  >
                    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.3rem" }}>
                      <span className="trb-badge-red" style={{ backgroundColor: STATUS_COLOR[art.status] || "var(--fg-ink)" }}>
                        {art.status}
                      </span>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", opacity: 0.7 }}>
                        {art.category}
                      </span>
                    </div>
                    <h4 style={{ fontSize: "0.95rem", fontFamily: "var(--font-headline)", fontWeight: 800, lineHeight: 1.25, marginBottom: "0.35rem" }}>
                      {art.title}
                    </h4>
                    <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "var(--font-mono)", fontSize: "0.7rem", opacity: 0.75 }}>
                      <span>BY: {art.author.username.toUpperCase()}</span>
                      <span>{new Date(art.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Article Detail Panel */}
          <section>
            {selectedArticle ? (
              <div className="trb-sidebar-card" style={{ padding: "1.75rem" }}>
                {/* Action Buttons Header */}
                {selectedArticle.status === "SUBMITTED" && (
                  <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
                    <button
                      onClick={() => handlePublish(selectedArticle.id)}
                      className="trb-btn-solid"
                      style={{ flex: 1, backgroundColor: "darkgreen", padding: "0.75rem" }}
                    >
                      ✓ APPROVE & PUBLISH TO FRONT PAGE
                    </button>
                    <a
                      href="#reject-section"
                      className="trb-btn-pill"
                      style={{ flex: 1, textAlign: "center", borderColor: "var(--accent-red)", color: "var(--accent-red)", textDecoration: "none", padding: "0.75rem" }}
                    >
                      ✗ REJECT WITH EDITORIAL FEEDBACK
                    </a>
                  </div>
                )}

                {selectedArticle.status === "PUBLISHED" && (
                  <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--border-color)", paddingBottom: "1rem" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", color: "darkgreen", fontWeight: 800 }}>
                      ✓ DISPATCH IS LIVE · {selectedArticle.view_count} REVIEWS
                    </span>
                    <a
                      href={siteUrl(`/articles/${selectedArticle.slug}`)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="trb-btn-solid"
                      style={{ textDecoration: "none" }}
                    >
                      VIEW ON LIVE BROADSHEET ↗
                    </a>
                  </div>
                )}

                {/* Article Content */}
                <div style={{ border: "1px solid var(--border-color)", padding: "1.75rem", marginBottom: "1.5rem", backgroundColor: "var(--bg-paper)", maxHeight: "420px", overflowY: "auto", borderRadius: "3px" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", opacity: 0.7, display: "block", marginBottom: "0.5rem", textTransform: "uppercase" }}>
                    EDITORIAL REVIEW PROOF — {selectedArticle.status}
                  </span>
                  <h2 style={{ fontFamily: "var(--font-headline)", fontSize: "1.8rem", textTransform: "uppercase", lineHeight: 1.1, fontWeight: 900, marginBottom: "0.75rem" }}>
                    {selectedArticle.title}
                  </h2>
                  <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", opacity: 0.8, marginBottom: "1.25rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.5rem" }}>
                    BY: {selectedArticle.author.username.toUpperCase()} · CATEGORY: {selectedArticle.category.toUpperCase()} · DATE: {new Date(selectedArticle.created_at).toLocaleDateString()}
                  </p>
                  <div
                    style={{ fontSize: "1rem", lineHeight: 1.7 }}
                    dangerouslySetInnerHTML={{ __html: selectedArticle.content }}
                  />
                </div>

                {/* Review Notes Form */}
                <div id="reject-section" style={{ border: "2px double var(--border-color)", padding: "1.5rem", borderRadius: "3px" }}>
                  <h4 style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 800, textTransform: "uppercase", marginBottom: "0.75rem" }}>
                    EDITORIAL REVIEW NOTES & AUDIT LOG
                  </h4>

                  <div style={{ maxHeight: "160px", overflowY: "auto", marginBottom: "1.25rem" }}>
                    {reviews.length === 0 ? (
                      <p style={{ fontStyle: "italic", fontSize: "0.85rem", opacity: 0.7 }}>No editorial notes recorded for this article.</p>
                    ) : reviews.map(rev => (
                      <div key={rev.id} style={{ fontSize: "0.85rem", marginBottom: "0.75rem", paddingBottom: "0.6rem", borderBottom: "1px dashed var(--border-color)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "var(--font-mono)", fontSize: "0.7rem", opacity: 0.8, marginBottom: "0.2rem" }}>
                          <span>BY: {rev.author.username.toUpperCase()} ({rev.author.role})</span>
                          <span>{new Date(rev.created_at).toLocaleDateString()}</span>
                        </div>
                        <p>{rev.content}</p>
                      </div>
                    ))}
                  </div>

                  <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }}>
                    ADD EDITORIAL FEEDBACK NOTE:
                  </label>
                  <textarea
                    value={feedback}
                    onChange={e => setFeedback(e.target.value)}
                    placeholder="Enter corrections, revisions required, or rejection rationale..."
                    className="trb-input"
                    style={{ width: "100%", height: "90px", resize: "vertical", fontFamily: "var(--font-body)", marginBottom: "0.75rem" }}
                    disabled={submittingReview}
                  />

                  <div style={{ display: "flex", gap: "0.75rem" }}>
                    <button
                      onClick={handleSendNote}
                      className="trb-btn-solid"
                      disabled={submittingReview || !feedback.trim()}
                    >
                      SEND NOTE
                    </button>
                    {selectedArticle.status === "SUBMITTED" && (
                      <button
                        onClick={handleReject}
                        className="trb-btn-pill"
                        style={{ borderColor: "var(--accent-red)", color: "var(--accent-red)" }}
                        disabled={submittingReview || !feedback.trim()}
                      >
                        {submittingReview ? "PROCESSING..." : "REJECT & RETURN TO WRITER"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="trb-sidebar-card" style={{ padding: "5rem 2rem", textAlign: "center" }}>
                <h4 style={{ fontFamily: "var(--font-headline)", fontSize: "1.6rem", textTransform: "uppercase", marginBottom: "0.75rem" }}>
                  NO DISPATCH SELECTED
                </h4>
                <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", opacity: 0.8 }}>
                  Select a story from the queue on the left to review proof copy and issue editorial decisions.
                </p>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
