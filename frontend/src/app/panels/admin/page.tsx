"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import RichTextEditor from "../../components/RichTextEditor";
import { apiErrorMessage, apiFetch } from "../../../lib/auth";
import { apiUrl } from "../../../lib/config";

type Tab = "dashboard" | "users" | "articles" | "inbox";
type Role = "READER" | "JOURNALIST" | "EDITOR" | "ADMIN" | "SUPER_ADMIN";
type Status = "DRAFT" | "FACT_CHECK" | "EDITOR_REVIEW" | "APPROVED" | "SCHEDULED" | "SUBMITTED" | "PUBLISHED" | "REJECTED";
type ArticleType = "NEWS" | "OPINION" | "INVESTIGATION" | "FACT_CHECK" | "LIVE";

interface User {
  id: number;
  username: string;
  email?: string | null;
  bio?: string | null;
  slug?: string | null;
  profile_image_url?: string | null;
  job_title?: string | null;
  coverage_areas?: string | null;
  social_links?: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
}

interface Article {
  id: number;
  slug: string;
  title: string;
  subtitle?: string | null;
  summary: string;
  content: string;
  category: string;
  image_url?: string | null;
  image_caption?: string | null;
  tags?: string | null;
  sources?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
  og_image_url?: string | null;
  article_type: ArticleType;
  fact_check_rating?: string | null;
  scheduled_at?: string | null;
  status: Status;
  view_count: number;
  is_pinned: boolean;
  is_breaking: boolean;
  created_at: string;
  author: { id?: number; username: string };
}

interface Stats {
  total_users: number;
  total_articles: number;
  published_articles: number;
  draft_articles: number;
  submitted_articles: number;
  fact_check_articles?: number;
  editor_review_articles?: number;
  approved_articles?: number;
  scheduled_articles?: number;
  total_corrections?: number;
  rejected_articles: number;
  total_comments: number;
  total_journalists: number;
  total_editors: number;
  total_readers: number;
}

interface NewsroomMessage {
  id: number;
  purpose: string;
  name?: string | null;
  email?: string | null;
  message: string;
  status: string;
  created_at: string;
}

const EMPTY_USER = { username: "", email: "", password: "", role: "READER" as Role, bio: "", profile_image_url: "", job_title: "", coverage_areas: "", social_links: "", is_active: true };
const EMPTY_ARTICLE = { author_id: "", title: "", subtitle: "", summary: "", content: "", category: "General", article_type: "NEWS" as ArticleType, fact_check_rating: "", image_url: "", image_caption: "", og_image_url: "", tags: "", sources: "", seo_title: "", seo_description: "", scheduled_at: "", is_pinned: false, is_breaking: false };
const STATUS_COLOR: Record<Status, string> = { PUBLISHED: "#35613d", DRAFT: "#666", FACT_CHECK: "#8a5a16", EDITOR_REVIEW: "#214c7a", APPROVED: "#35613d", SCHEDULED: "#6b3f83", SUBMITTED: "#214c7a", REJECTED: "var(--accent-red)" };

export default function AdminPanel() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [messages, setMessages] = useState<NewsroomMessage[]>([]);
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [userSearch, setUserSearch] = useState("");
  const [articleSearch, setArticleSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [userFormOpen, setUserFormOpen] = useState(false);
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [userForm, setUserForm] = useState(EMPTY_USER);

  const [articleFormOpen, setArticleFormOpen] = useState(false);
  const [editingArticleId, setEditingArticleId] = useState<number | null>(null);
  const [articleForm, setArticleForm] = useState(EMPTY_ARTICLE);

  const request = useCallback(async <T,>(path: string, options?: RequestInit): Promise<T> => {
    const response = await apiFetch(apiUrl(path), options);
    if (!response.ok) throw new Error(await apiErrorMessage(response));
    return response.json();
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const suffix = statusFilter === "ALL" ? "" : `?status_filter=${statusFilter}`;
      const [me, metrics, people, stories, inbox] = await Promise.all([
        request<User>("/api/auth/me"),
        request<Stats>("/api/admin/stats"),
        request<User[]>("/api/admin/users"),
        request<Article[]>(`/api/admin/articles${suffix}`),
        request<NewsroomMessage[]>("/api/newsroom/messages"),
      ]);
      setCurrentUser(me);
      setStats(metrics);
      setUsers(people);
      setArticles(stories);
      setMessages(inbox);
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Could not load administration data" });
    } finally {
      setLoading(false);
    }
  }, [request, statusFilter]);

  useEffect(() => { refresh(); }, [refresh]);

  const roles: Role[] = currentUser?.role === "SUPER_ADMIN"
    ? ["READER", "JOURNALIST", "EDITOR", "ADMIN", "SUPER_ADMIN"]
    : ["READER", "JOURNALIST", "EDITOR"];

  const visibleUsers = useMemo(() => {
    const query = userSearch.trim().toLowerCase();
    if (!query) return users;
    return users.filter((user) => [user.username, user.email, user.role, user.bio]
      .some((value) => value?.toLowerCase().includes(query)));
  }, [userSearch, users]);

  const visibleArticles = useMemo(() => {
    const query = articleSearch.trim().toLowerCase();
    if (!query) return articles;
    return articles.filter((article) => [article.title, article.author.username, article.category, article.tags, article.summary]
      .some((value) => value?.toLowerCase().includes(query)));
  }, [articleSearch, articles]);

  const openNewUser = () => {
    setEditingUserId(null);
    setUserForm(EMPTY_USER);
    setUserFormOpen(true);
  };

  const openEditUser = (user: User) => {
    setEditingUserId(user.id);
    setUserForm({ username: user.username, email: user.email || "", password: "", role: user.role, bio: user.bio || "", profile_image_url: user.profile_image_url || "", job_title: user.job_title || "", coverage_areas: user.coverage_areas || "", social_links: user.social_links || "", is_active: user.is_active });
    setUserFormOpen(true);
  };

  const saveUser = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setNotice(null);
    try {
      const editing = editingUserId !== null;
      const body = editing
        ? { email: userForm.email || null, bio: userForm.bio || null, profile_image_url: userForm.profile_image_url || null, job_title: userForm.job_title || null, coverage_areas: userForm.coverage_areas || null, social_links: userForm.social_links || null, role: userForm.role, is_active: userForm.is_active }
        : { ...userForm, email: userForm.email || null, bio: userForm.bio || null, profile_image_url: userForm.profile_image_url || null, job_title: userForm.job_title || null, coverage_areas: userForm.coverage_areas || null, social_links: userForm.social_links || null };
      await request(editing ? `/api/admin/users/${editingUserId}` : "/api/admin/users", {
        method: editing ? "PUT" : "POST",
        body: JSON.stringify(body),
      });
      setNotice({ type: "success", text: editing ? "User account updated." : "User account created." });
      setUserFormOpen(false);
      await refresh();
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "User operation failed" });
    } finally { setBusy(false); }
  };

  const deleteUser = async (user: User) => {
    if (!window.confirm(`Delete ${user.username}? Accounts with publication history will be preserved and must be suspended instead.`)) return;
    setBusy(true);
    try {
      await request(`/api/admin/users/${user.id}`, { method: "DELETE" });
      setNotice({ type: "success", text: `${user.username} was deleted.` });
      await refresh();
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Delete failed" });
    } finally { setBusy(false); }
  };

  const openNewArticle = () => {
    setEditingArticleId(null);
    setArticleForm(EMPTY_ARTICLE);
    setArticleFormOpen(true);
  };

  const openEditArticle = (article: Article) => {
    setEditingArticleId(article.id);
    setArticleForm({
      author_id: String(article.author.id || ""),
      title: article.title,
      subtitle: article.subtitle || "",
      summary: article.summary || "",
      content: article.content,
      category: article.category,
      article_type: article.article_type || "NEWS",
      fact_check_rating: article.fact_check_rating || "",
      image_url: article.image_url || "",
      image_caption: article.image_caption || "",
      og_image_url: article.og_image_url || "",
      tags: article.tags || "",
      sources: article.sources || "",
      seo_title: article.seo_title || "",
      seo_description: article.seo_description || "",
      scheduled_at: article.scheduled_at ? article.scheduled_at.slice(0, 16) : "",
      is_pinned: article.is_pinned,
      is_breaking: article.is_breaking,
    });
    setArticleFormOpen(true);
  };

  const saveArticle = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setNotice(null);
    try {
      const editing = editingArticleId !== null;
      const payload = {
        ...articleForm,
        author_id: articleForm.author_id ? Number(articleForm.author_id) : undefined,
        subtitle: articleForm.subtitle.trim() || null,
        image_url: articleForm.image_url.trim() || null,
        image_caption: articleForm.image_url.trim() ? articleForm.image_caption.trim() || null : null,
        og_image_url: articleForm.og_image_url.trim() || null,
        tags: articleForm.tags.trim() || null,
        sources: articleForm.sources.trim() || null,
        seo_title: articleForm.seo_title.trim() || null,
        seo_description: articleForm.seo_description.trim() || null,
        fact_check_rating: articleForm.article_type === "FACT_CHECK" ? articleForm.fact_check_rating || null : null,
        scheduled_at: articleForm.scheduled_at ? new Date(articleForm.scheduled_at).toISOString() : null,
      };
      const saved = await request<Article>(editing ? `/api/articles/${editingArticleId}` : "/api/articles", {
        method: editing ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      if (!editing && (articleForm.is_pinned || articleForm.is_breaking)) {
        await request(`/api/articles/${saved.id}`, {
          method: "PUT",
          body: JSON.stringify({ is_pinned: articleForm.is_pinned, is_breaking: articleForm.is_breaking }),
        });
      }
      setNotice({ type: "success", text: editing ? "Article updated." : "Article draft created." });
      setArticleFormOpen(false);
      await refresh();
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Article operation failed" });
    } finally { setBusy(false); }
  };

  const changeArticleStatus = async (article: Article, status: Status) => {
    if (!window.confirm(`Change “${article.title}” to ${status}?`)) return;
    setBusy(true);
    try {
      await request(`/api/articles/${article.id}`, { method: "PUT", body: JSON.stringify({ status }) });
      setNotice({ type: "success", text: `Article moved to ${status}.` });
      await refresh();
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Status update failed" });
    } finally { setBusy(false); }
  };

  const deleteArticle = async (article: Article) => {
    if (!window.confirm(`Permanently delete “${article.title}”?`)) return;
    setBusy(true);
    try {
      await request(`/api/articles/${article.id}`, { method: "DELETE" });
      setNotice({ type: "success", text: "Article deleted." });
      await refresh();
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Delete failed" });
    } finally { setBusy(false); }
  };

  const metrics = stats ? [
    ["Users", stats.total_users], ["Articles", stats.total_articles], ["Published", stats.published_articles],
    ["In review", (stats.submitted_articles || 0) + (stats.editor_review_articles || 0)], ["Fact check", stats.fact_check_articles || 0], ["Approved", stats.approved_articles || 0], ["Scheduled", stats.scheduled_articles || 0], ["Drafts", stats.draft_articles], ["Corrections", stats.total_corrections || 0], ["Comments", stats.total_comments],
  ] : [];

  return (
    <div className="crud-panel">
      <div className="crud-heading">
        <div><p className="eyebrow">Publication operations</p><h2>Content & account control</h2></div>
        <button className="trb-btn-pill" onClick={refresh} disabled={loading}>Refresh records</button>
      </div>

      {notice && <div className={`crud-notice ${notice.type}`} role="status">{notice.text}</div>}

      <div className="crud-tabs" role="tablist">
        {(["dashboard", "users", "articles", "inbox"] as Tab[]).map((item) => (
          <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>
        ))}
      </div>

      {tab === "dashboard" && (
        <section>
          <div className="metric-grid">{metrics.map(([label, value]) => <div className="metric-card" key={label}><strong>{value}</strong><span>{label}</span></div>)}</div>
          <div className="crud-quick-actions"><button className="trb-btn-solid" onClick={() => { setTab("users"); openNewUser(); }}>Add user</button><button className="trb-btn-solid" onClick={() => { setTab("articles"); openNewArticle(); }}>Add article</button></div>
        </section>
      )}

      {tab === "users" && (
        <section>
          <div className="crud-section-heading"><div><h3>User registry</h3><p>Create, inspect, edit, suspend, or remove accounts.</p></div><button className="trb-btn-solid" onClick={openNewUser}>+ Add user</button></div>
          <div className="crud-filter"><label>Search users <input className="trb-input" value={userSearch} onChange={(event) => setUserSearch(event.target.value)} placeholder="Name, email, role, or bio…" /></label><span>{visibleUsers.length} of {users.length} accounts</span></div>
          {userFormOpen && (
            <form className="crud-form" onSubmit={saveUser}>
              <div className="crud-form-title"><h3>{editingUserId ? "Edit account" : "Create account"}</h3><button type="button" onClick={() => setUserFormOpen(false)}>Close</button></div>
              <div className="crud-form-grid">
                <label>Username<input value={userForm.username} onChange={(e) => setUserForm({ ...userForm, username: e.target.value })} disabled={editingUserId !== null} minLength={3} required /></label>
                <label>Email<input type="email" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} /></label>
                {!editingUserId && <label>Temporary password<input type="password" value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} minLength={8} required /></label>}
                <label>Role<select value={userForm.role} onChange={(e) => setUserForm({ ...userForm, role: e.target.value as Role })}>{roles.map((role) => <option key={role}>{role}</option>)}</select></label>
                <label className="crud-wide">Bio<textarea value={userForm.bio} onChange={(e) => setUserForm({ ...userForm, bio: e.target.value })} rows={3} /></label>
                <label>Newsroom title<input value={userForm.job_title} onChange={(e) => setUserForm({ ...userForm, job_title: e.target.value })} placeholder="Reporter, editor…" /></label>
                <label>Profile image URL<input type="url" value={userForm.profile_image_url} onChange={(e) => setUserForm({ ...userForm, profile_image_url: e.target.value })} /></label>
                <label className="crud-wide">Areas of coverage<input value={userForm.coverage_areas} onChange={(e) => setUserForm({ ...userForm, coverage_areas: e.target.value })} placeholder="Politics, courts, technology" /></label>
                <label className="crud-wide">Profile links<textarea value={userForm.social_links} onChange={(e) => setUserForm({ ...userForm, social_links: e.target.value })} rows={2} placeholder="One public profile URL per line" /></label>
                {editingUserId && <label className="crud-check"><input type="checkbox" checked={userForm.is_active} onChange={(e) => setUserForm({ ...userForm, is_active: e.target.checked })} /> Account active</label>}
              </div>
              <button className="trb-btn-solid" disabled={busy}>{busy ? "Saving…" : "Save account"}</button>
            </form>
          )}
          <div className="crud-list">
            {visibleUsers.map((user) => (
              <article className="crud-row" key={user.id}>
                <div className="crud-primary"><strong>{user.username}</strong><span>{user.email || "No email"} · Joined {new Date(user.created_at).toLocaleDateString()}</span></div>
                <span className={`status-pill ${user.is_active ? "active" : "inactive"}`}>{user.is_active ? user.role.replace("_", " ") : "Suspended"}</span>
                <div className="crud-actions"><button onClick={() => openEditUser(user)}>Edit</button><button className="danger" onClick={() => deleteUser(user)} disabled={busy || currentUser?.id === user.id}>Delete</button></div>
              </article>
            ))}
            {visibleUsers.length === 0 && <p className="empty-copy">No accounts match this search.</p>}
          </div>
        </section>
      )}

      {tab === "articles" && (
        <section>
          <div className="crud-section-heading"><div><h3>Article archive</h3><p>Create drafts, revise copy, control status, and delete stories.</p></div><button className="trb-btn-solid" onClick={openNewArticle}>+ Add article</button></div>
          <div className="crud-filter"><label>Status <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option>ALL</option><option>DRAFT</option><option>FACT_CHECK</option><option>EDITOR_REVIEW</option><option>APPROVED</option><option>SCHEDULED</option><option>SUBMITTED</option><option>PUBLISHED</option><option>REJECTED</option></select></label><label>Search articles <input className="trb-input" value={articleSearch} onChange={(event) => setArticleSearch(event.target.value)} placeholder="Headline, author, category, or tag…" /></label><span>{visibleArticles.length} records</span></div>
          {articleFormOpen && (
            <form className="crud-form" onSubmit={saveArticle}>
              <div className="crud-form-title"><h3>{editingArticleId ? "Edit article" : "Create article draft"}</h3><button type="button" onClick={() => setArticleFormOpen(false)}>Close</button></div>
              <div className="crud-form-grid">
                <label>Author<select value={articleForm.author_id} onChange={(e) => setArticleForm({ ...articleForm, author_id: e.target.value })}><option value="">Current administrator</option>{users.filter((user) => ["JOURNALIST", "EDITOR", "ADMIN", "SUPER_ADMIN"].includes(user.role)).map((user) => <option key={user.id} value={user.id}>{user.username}</option>)}</select></label>
                <label className="crud-wide">Headline<input value={articleForm.title} onChange={(e) => setArticleForm({ ...articleForm, title: e.target.value })} minLength={5} required /></label>
                <label className="crud-wide">Subheadline / deck<input value={articleForm.subtitle} onChange={(e) => setArticleForm({ ...articleForm, subtitle: e.target.value })} maxLength={300} /></label>
                <label className="crud-wide">Summary<textarea value={articleForm.summary} onChange={(e) => setArticleForm({ ...articleForm, summary: e.target.value })} minLength={10} maxLength={800} required rows={3} /></label>
                <label>Category<input value={articleForm.category} onChange={(e) => setArticleForm({ ...articleForm, category: e.target.value })} required /></label>
                <label>Story type<select value={articleForm.article_type} onChange={(e) => setArticleForm({ ...articleForm, article_type: e.target.value as ArticleType })}><option value="NEWS">News</option><option value="OPINION">Opinion</option><option value="INVESTIGATION">Investigation</option><option value="FACT_CHECK">Fact check</option><option value="LIVE">Live coverage</option></select></label>
                {articleForm.article_type === "FACT_CHECK" && <label>Fact-check rating<select value={articleForm.fact_check_rating} onChange={(e) => setArticleForm({ ...articleForm, fact_check_rating: e.target.value })}><option value="">Pending verdict</option><option value="TRUE">True</option><option value="FALSE">False</option><option value="PARTLY_TRUE">Partly true</option><option value="MISLEADING">Misleading</option><option value="UNVERIFIED">Unverified</option></select></label>}
                <label>Tags<input value={articleForm.tags} onChange={(e) => setArticleForm({ ...articleForm, tags: e.target.value })} /></label>
                <label className="crud-wide">Image URL<input type="url" value={articleForm.image_url} onChange={(e) => setArticleForm({ ...articleForm, image_url: e.target.value })} /></label>
                <label className="crud-wide">Image caption<input value={articleForm.image_caption} onChange={(e) => setArticleForm({ ...articleForm, image_caption: e.target.value })} disabled={!articleForm.image_url.trim()} maxLength={300} /></label>
                <label className="crud-wide">Social preview image URL<input type="url" value={articleForm.og_image_url} onChange={(e) => setArticleForm({ ...articleForm, og_image_url: e.target.value })} /></label>
                <label className="crud-wide">Sources / references<textarea value={articleForm.sources} onChange={(e) => setArticleForm({ ...articleForm, sources: e.target.value })} rows={4} maxLength={5000} placeholder="One source or reference per line" /></label>
                <label className="crud-wide">SEO title<input value={articleForm.seo_title} onChange={(e) => setArticleForm({ ...articleForm, seo_title: e.target.value })} maxLength={220} /></label>
                <label className="crud-wide">SEO description<textarea value={articleForm.seo_description} onChange={(e) => setArticleForm({ ...articleForm, seo_description: e.target.value })} rows={2} maxLength={500} /></label>
                <label>Publication time<input type="datetime-local" value={articleForm.scheduled_at} onChange={(e) => setArticleForm({ ...articleForm, scheduled_at: e.target.value })} /></label>
                <label className="crud-check"><input type="checkbox" checked={articleForm.is_pinned} onChange={(e) => setArticleForm({ ...articleForm, is_pinned: e.target.checked })} /> Lead story</label>
                <label className="crud-check"><input type="checkbox" checked={articleForm.is_breaking} onChange={(e) => setArticleForm({ ...articleForm, is_breaking: e.target.checked })} /> Breaking news</label>
              </div>
              <label className="crud-editor-label">Article body *</label>
              <RichTextEditor value={articleForm.content} onChange={(content) => setArticleForm((form) => ({ ...form, content }))} placeholder="Write the article…" />
              <button className="trb-btn-solid" disabled={busy}>{busy ? "Saving…" : editingArticleId ? "Save article" : "Create draft"}</button>
            </form>
          )}
          <div className="crud-list">
            {visibleArticles.map((article) => (
              <article className="crud-row article-row" key={article.id}>
                <div className="crud-primary"><strong>{article.title}</strong><span>By {article.author.username} · {article.category} · {article.view_count} reads</span></div>
                <span className="status-pill" style={{ borderColor: STATUS_COLOR[article.status], color: STATUS_COLOR[article.status] }}>{article.status}</span>
                <div className="crud-actions">
                  <button onClick={() => openEditArticle(article)}>Edit</button>
                  {(article.status === "DRAFT" || article.status === "REJECTED") && <button onClick={() => changeArticleStatus(article, "FACT_CHECK")}>Fact check</button>}
                  {article.status === "FACT_CHECK" && <button onClick={() => changeArticleStatus(article, "EDITOR_REVIEW")}>Editor review</button>}
                  {(article.status === "EDITOR_REVIEW" || article.status === "SUBMITTED") && <button onClick={() => changeArticleStatus(article, "APPROVED")}>Approve</button>}
                  {article.status === "APPROVED" && article.scheduled_at && <button onClick={() => changeArticleStatus(article, "SCHEDULED")}>Schedule</button>}
                  {["FACT_CHECK", "EDITOR_REVIEW", "APPROVED", "SCHEDULED", "SUBMITTED"].includes(article.status) && <button onClick={() => changeArticleStatus(article, "PUBLISHED")}>Publish</button>}
                  {article.status === "PUBLISHED" && <button onClick={() => changeArticleStatus(article, "DRAFT")}>Unpublish</button>}
                  {article.status === "PUBLISHED" && <Link href={`/articles/${article.slug}`}>View</Link>}
                  <button className="danger" onClick={() => deleteArticle(article)} disabled={busy}>Delete</button>
                </div>
              </article>
            ))}
            {visibleArticles.length === 0 && <p className="empty-copy">No articles match the selected filters.</p>}
          </div>
        </section>
      )}

      {tab === "inbox" && (
        <section>
          <div className="crud-section-heading"><div><h3>Newsroom inbox</h3><p>Messages submitted through the public contact form. Standard web submissions are not represented as secure or anonymous.</p></div><span>{messages.length} messages</span></div>
          <div className="corrections-ledger">
            {messages.map((message) => <article key={message.id}><div className="crud-section-heading"><div><p className="eyebrow">{message.purpose} · {message.status}</p><h2>{message.name || "Name not supplied"}</h2></div><time>{new Date(message.created_at).toLocaleString()}</time></div><p>{message.message}</p>{message.email && <a href={`mailto:${message.email}`}>{message.email}</a>}</article>)}
            {messages.length === 0 && <p className="empty-copy">No newsroom messages have been received.</p>}
          </div>
        </section>
      )}
    </div>
  );
}
