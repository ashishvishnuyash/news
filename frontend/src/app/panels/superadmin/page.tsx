"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { apiErrorMessage, apiFetch } from "../../../lib/auth";
import { apiUrl } from "../../../lib/config";
import type { SiteSettings, User } from "../../../lib/types";

export default function SuperAdminPanel() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [siteName, setSiteName] = useState("The Republic Bulletin");
  const [siteMotto, setSiteMotto] = useState("The Voice of Truth, Unfiltered & Uncompromised");
  const [breakingNews, setBreakingNews] = useState("");
  const [breakingActive, setBreakingActive] = useState(true);
  const [categories, setCategories] = useState<string[]>([]);
  const [newCatInput, setNewCatInput] = useState("");
  const [commentsEnabled, setCommentsEnabled] = useState(true);
  const [registrationOpen, setRegistrationOpen] = useState(true);
  const [maintenanceMode, setMaintenanceMode] = useState(false);

  const [users, setUsers] = useState<User[]>([]);

  useEffect(() => {
    apiFetch(apiUrl("/api/auth/me"))
      .then((res) => {
        if (!res.ok) throw new Error("Unauthorized");
        return res.json();
      })
      .then((userData) => {
        if (userData.role !== "SUPER_ADMIN") {
          setError("Access Denied: Super Admin privileges required.");
          setLoading(false);
          return;
        }
        setUser(userData);
        loadSettings();
        loadUsers();
      })
      .catch((err) => {
        console.error(err);
        setError("You must be logged in as Super Admin.");
        setLoading(false);
      });
  }, []);

  const loadSettings = async () => {
    try {
      const res = await fetch(apiUrl("/api/settings"));
      if (res.ok) {
        const data: Partial<SiteSettings> = await res.json();
        if (data.site_name) setSiteName(data.site_name);
        if (data.site_motto) setSiteMotto(data.site_motto);
        if (data.breaking_news) setBreakingNews(data.breaking_news);
        if (data.breaking_active !== undefined) setBreakingActive(data.breaking_active === true || String(data.breaking_active).toLowerCase() === "true");
        if (data.categories) setCategories(Array.isArray(data.categories) ? data.categories : []);
        if (data.features) {
          const feats = data.features;
          if (feats.comments_enabled !== undefined) setCommentsEnabled(feats.comments_enabled);
          if (feats.registration_open !== undefined) setRegistrationOpen(feats.registration_open);
          if (feats.maintenance_mode !== undefined) setMaintenanceMode(feats.maintenance_mode);
        }
      }
    } catch (err) {
      console.error("Error loading settings:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const res = await apiFetch(apiUrl("/api/admin/users"));
      if (res.ok) setUsers(await res.json());
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      const payload = {
        site_name: siteName,
        site_motto: siteMotto,
        breaking_news: breakingNews,
        breaking_active: breakingActive,
        categories: categories,
        features: {
          comments_enabled: commentsEnabled,
          registration_open: registrationOpen,
          maintenance_mode: maintenanceMode,
        },
      };

      const res = await apiFetch(apiUrl("/api/settings"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to update settings");
      }

      setSuccess("Site settings updated successfully across the publication network!");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An error occurred");
    }
  };

  const handleAddCategory = () => {
    if (!newCatInput.trim()) return;
    const catName = newCatInput.trim();
    if (!categories.includes(catName)) {
      setCategories([...categories, catName]);
    }
    setNewCatInput("");
  };

  const handleRemoveCategory = (catToRemove: string) => {
    setCategories(categories.filter((c) => c !== catToRemove));
  };

  const handleUserRoleChange = async (userId: number, newRole: string) => {
    try {
      const res = await apiFetch(apiUrl(`/api/admin/users/${userId}/role`), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: newRole }),
      });
      if (res.ok) {
        setSuccess(`User ID ${userId} role updated to ${newRole}`);
        loadUsers();
      } else {
        setError(await apiErrorMessage(res, "Role update failed"));
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "6rem 1rem", fontFamily: "var(--font-mono)", fontSize: "0.85rem", letterSpacing: "2px", textTransform: "uppercase" }}>
        👑 AUTHENTICATING SUPER ADMIN ACCESS...
      </div>
    );
  }

  if (error && !user) {
    return (
      <div style={{ maxWidth: "600px", margin: "4rem auto", padding: "2.5rem", border: "4px double var(--accent-red)", backgroundColor: "var(--card-bg)", textAlign: "center" }}>
        <h1 style={{ fontFamily: "var(--font-headline)", fontSize: "2rem", color: "var(--accent-red)", textTransform: "uppercase", marginBottom: "0.5rem" }}>
          SECURITY LOCKOUT
        </h1>
        <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
          {error}
        </p>
        <Link href="/login" className="trb-btn-solid" style={{ textDecoration: "none" }}>
          RETURN TO LOGIN
        </Link>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* Header Banner */}
      <div style={{ borderBottom: "3px double var(--border-color)", paddingBottom: "1rem", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <span className="trb-badge-red" style={{ backgroundColor: "purple" }}>
            👑 SUPER ADMIN COMMAND DESK
          </span>
          <h1 style={{ fontFamily: "var(--font-headline)", fontSize: "2rem", fontWeight: 900, textTransform: "uppercase", margin: "0.4rem 0 0" }}>
            CENTRAL PUBLICATION CONTROL
          </h1>
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", fontWeight: 700 }}>
          LOGGED IN: <strong>{user?.username?.toUpperCase()}</strong>
        </div>
      </div>

      {success && (
        <div style={{ padding: "0.85rem", border: "1px solid darkgreen", backgroundColor: "rgba(0,100,0,0.05)", color: "darkgreen", fontFamily: "var(--font-mono)", fontSize: "0.8rem", fontWeight: 700 }}>
          ✓ {success}
        </div>
      )}

      {error && (
        <div style={{ padding: "0.85rem", border: "1px solid var(--accent-red)", backgroundColor: "rgba(139,0,0,0.05)", color: "var(--accent-red)", fontFamily: "var(--font-mono)", fontSize: "0.8rem", fontWeight: 700 }}>
          ⚠️ {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "2rem" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "2rem" }}>
          {/* Main Form */}
          <form onSubmit={handleSaveSettings} className="trb-sidebar-card" style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
            <h2 className="trb-sidebar-heading" style={{ fontSize: "1.2rem" }}>
              1. Global Publication Branding & Motto
            </h2>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }}>
                  Publication Title:
                </label>
                <input
                  type="text"
                  value={siteName}
                  onChange={(e) => setSiteName(e.target.value)}
                  className="trb-input"
                  style={{ width: "100%", fontSize: "1.1rem", fontFamily: "var(--font-headline)", fontWeight: 700 }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }}>
                  Masthead Motto / Tagline:
                </label>
                <input
                  type="text"
                  value={siteMotto}
                  onChange={(e) => setSiteMotto(e.target.value)}
                  className="trb-input"
                  style={{ width: "100%", fontStyle: "italic", fontFamily: "var(--font-headline)" }}
                />
              </div>
            </div>

            <h2 className="trb-sidebar-heading" style={{ fontSize: "1.2rem" }}>
              2. Live Breaking News Broadcast Ticker
            </h2>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <input
                  type="checkbox"
                  id="breakingActive"
                  checked={breakingActive}
                  onChange={(e) => setBreakingActive(e.target.checked)}
                  style={{ width: "18px", height: "18px", accentColor: "var(--accent-red)" }}
                />
                <label htmlFor="breakingActive" style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, cursor: "pointer" }}>
                  BROADCAST TICKER ACTIVE ON FRONT PAGE
                </label>
              </div>

              <div>
                <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }}>
                  Live Broadcast Alert Text:
                </label>
                <textarea
                  value={breakingNews}
                  onChange={(e) => setBreakingNews(e.target.value)}
                  rows={2}
                  className="trb-input"
                  style={{ width: "100%", resize: "vertical" }}
                  placeholder="Enter breaking headline..."
                />
              </div>
            </div>

            <h2 className="trb-sidebar-heading" style={{ fontSize: "1.2rem" }}>
              3. Category Taxonomy Management
            </h2>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input
                  type="text"
                  value={newCatInput}
                  onChange={(e) => setNewCatInput(e.target.value)}
                  placeholder="New Category Name..."
                  className="trb-input"
                  style={{ flexGrow: 1 }}
                />
                <button type="button" onClick={handleAddCategory} className="trb-btn-solid">
                  ADD CATEGORY
                </button>
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                {categories.map((cat) => (
                  <span key={cat} className="trb-btn-pill" style={{ pointerEvents: "none", gap: "0.5rem" }}>
                    <span>{cat}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveCategory(cat)}
                      style={{ background: "none", border: "none", color: "var(--accent-red)", fontWeight: 900, cursor: "pointer", pointerEvents: "auto" }}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <h2 className="trb-sidebar-heading" style={{ fontSize: "1.2rem" }}>
              4. System Feature Flags & Security Controls
            </h2>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <input
                  type="checkbox"
                  id="commentsEnabled"
                  checked={commentsEnabled}
                  onChange={(e) => setCommentsEnabled(e.target.checked)}
                  style={{ width: "18px", height: "18px", accentColor: "var(--fg-ink)" }}
                />
                <label htmlFor="commentsEnabled" style={{ fontWeight: 700, cursor: "pointer" }}>
                  ALLOW PUBLIC READER COMMENTS
                </label>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <input
                  type="checkbox"
                  id="registrationOpen"
                  checked={registrationOpen}
                  onChange={(e) => setRegistrationOpen(e.target.checked)}
                  style={{ width: "18px", height: "18px", accentColor: "var(--fg-ink)" }}
                />
                <label htmlFor="registrationOpen" style={{ fontWeight: 700, cursor: "pointer" }}>
                  PUBLIC SUBSCRIBER REGISTRATION OPEN
                </label>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <input
                  type="checkbox"
                  id="maintenanceMode"
                  checked={maintenanceMode}
                  onChange={(e) => setMaintenanceMode(e.target.checked)}
                  style={{ width: "18px", height: "18px", accentColor: "var(--accent-red)" }}
                />
                <label htmlFor="maintenanceMode" style={{ fontWeight: 700, color: "var(--accent-red)", cursor: "pointer" }}>
                  MAINTENANCE MODE (SYSTEM LOCKOUT FOR NON-STAFF)
                </label>
              </div>
            </div>

            <div style={{ borderTop: "2px double var(--border-color)", paddingTop: "1.25rem" }}>
              <button type="submit" className="trb-btn-solid" style={{ width: "100%", padding: "0.85rem", fontSize: "0.85rem", letterSpacing: "1px" }}>
                SAVE & DEPLOY ALL SITE SETTINGS NETWORK-WIDE
              </button>
            </div>
          </form>

          {/* User Role Elevation Card */}
          <div className="trb-sidebar-card">
            <h2 className="trb-sidebar-heading" style={{ fontSize: "1.2rem" }}>
              Staff & User Access Elevation
            </h2>
            <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", opacity: 0.8, marginBottom: "1rem" }}>
              Manage system permissions across Super Admin, Admin, Editor, Journalist, and Reader.
            </p>
            <Link href="/panels/admin" className="trb-btn-solid" style={{ display: "inline-flex", textDecoration: "none", marginBottom: "1rem" }}>
              Open full user & article CRUD
            </Link>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxHeight: "360px", overflowY: "auto" }}>
              {users.map((u) => (
                <div key={u.id} style={{ border: "1px solid var(--border-color)", padding: "0.75rem", background: "var(--bg-paper)", borderRadius: "3px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontWeight: 800, fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>
                      {u.username}
                    </div>
                    <div style={{ fontSize: "0.7rem", fontFamily: "var(--font-mono)", opacity: 0.7 }}>
                      {u.email || "No Email"}
                    </div>
                  </div>

                  <select
                    value={u.role}
                    onChange={(e) => handleUserRoleChange(u.id, e.target.value)}
                    className="trb-select"
                  >
                    <option value="READER">READER</option>
                    <option value="JOURNALIST">JOURNALIST</option>
                    <option value="EDITOR">EDITOR</option>
                    <option value="ADMIN">ADMIN</option>
                    <option value="SUPER_ADMIN">SUPER ADMIN</option>
                  </select>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
