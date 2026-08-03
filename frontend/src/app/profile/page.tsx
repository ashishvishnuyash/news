"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "../../lib/auth";
import Link from "next/link";
import { apiUrl } from "../../lib/config";

interface UserProfile {
  id: number;
  username: string;
  role: string;
  email?: string;
  bio?: string;
  created_at: string;
}

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // Profile edit
  const [email, setEmail] = useState("");
  const [bio, setBio] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMsg, setProfileMsg] = useState("");

  // Password change
  const [currentPwd, setCurrentPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [pwdSaving, setPwdSaving] = useState(false);
  const [pwdMsg, setPwdMsg] = useState("");

  const fetchProfile = useCallback(async () => {
    try {
      const res = await apiFetch(apiUrl("/api/auth/me"));
      if (res.ok) {
        const data: UserProfile = await res.json();
        setUser(data);
        setEmail(data.email || "");
        setBio(data.bio || "");
      } else {
        router.push("/login");
      }
    } catch {
      router.push("/login");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    const timer = window.setTimeout(fetchProfile, 0);
    return () => window.clearTimeout(timer);
  }, [fetchProfile]);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileSaving(true);
    setProfileMsg("");
    try {
      const res = await apiFetch(apiUrl("/api/users/me/profile"), {
        method: "PUT",
        body: JSON.stringify({ email: email || null, bio }),
      });
      if (res.ok) {
        const updated = await res.json();
        setUser(updated);
        setProfileMsg("✓ Profile updated successfully.");
      } else {
        const err = await res.json();
        setProfileMsg(`✗ ${err.detail || "Failed to update profile."}`);
      }
    } catch {
      setProfileMsg("✗ Connection error. Please try again.");
    } finally {
      setProfileSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPwd !== confirmPwd) {
      setPwdMsg("✗ New passwords do not match.");
      return;
    }
    setPwdSaving(true);
    setPwdMsg("");
    try {
      const res = await apiFetch(apiUrl("/api/users/me/password"), {
        method: "PUT",
        body: JSON.stringify({
          current_password: currentPwd,
          new_password: newPwd,
          confirm_new_password: confirmPwd,
        }),
      });
      if (res.ok) {
        setCurrentPwd("");
        setNewPwd("");
        setConfirmPwd("");
        setPwdMsg("✓ Password changed successfully.");
      } else {
        const err = await res.json();
        setPwdMsg(`✗ ${err.detail || "Failed to change password."}`);
      }
    } catch {
      setPwdMsg("✗ Connection error. Please try again.");
    } finally {
      setPwdSaving(false);
    }
  };

  const handleLogout = async () => {
    await apiFetch(apiUrl("/api/auth/logout"), { method: "POST" }).catch(() => undefined);
    window.localStorage.removeItem("chronicle_token");
    router.push("/login");
  };

  if (loading) {
    return (
      <div className="trb-container" style={{ minHeight: "80vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center", fontFamily: "var(--font-mono)", fontSize: "0.85rem", letterSpacing: "2px", textTransform: "uppercase" }}>
          📜 LOADING SUBSCRIBER & PRESS DOSSIER...
        </div>
      </div>
    );
  }

  if (!user) return null;

  const roleBadgeColor: Record<string, string> = {
    SUPER_ADMIN: "purple",
    ADMIN: "var(--accent-red)",
    EDITOR: "navy",
    JOURNALIST: "darkgreen",
    READER: "var(--fg-ink)",
  };

  return (
    <div className="trb-container" style={{ maxWidth: "900px", margin: "2rem auto" }}>
      {/* Back */}
      <Link href="/" className="trb-btn-pill" style={{ textDecoration: "none", marginBottom: "1.5rem" }}>
        ← RETURN TO FRONT PAGE
      </Link>

      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: "2rem", borderBottom: "4px double var(--border-color)", paddingBottom: "1.5rem" }}>
        <p style={{ fontFamily: "var(--font-masthead)", fontSize: "1rem", letterSpacing: "2px", marginBottom: "0.25rem" }}>
          THE REPUBLIC BULLETIN
        </p>
        <h1 style={{ fontFamily: "var(--font-headline)", fontSize: "2.5rem", fontWeight: 900, textTransform: "uppercase", margin: 0 }}>
          SUBSCRIBER & PRESS DOSSIER
        </h1>
      </div>

      {/* Profile Summary Card */}
      <div className="trb-sidebar-card responsive-summary-grid" style={{ marginBottom: "2.5rem" }}>
        <div>
          <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, opacity: 0.7, marginBottom: "0.25rem" }}>PEN NAME / USERNAME</p>
          <p style={{ fontFamily: "var(--font-headline)", fontSize: "1.5rem", fontWeight: 900 }}>{user.username.toUpperCase()}</p>
        </div>
        <div>
          <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, opacity: 0.7, marginBottom: "0.25rem" }}>PRESS CREDENTIALS</p>
          <span className="trb-badge-red" style={{ backgroundColor: roleBadgeColor[user.role] || "var(--fg-ink)", fontSize: "0.8rem", padding: "0.3rem 0.75rem" }}>
            {user.role}
          </span>
        </div>
        <div>
          <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, opacity: 0.7, marginBottom: "0.25rem" }}>EMAIL ADDRESS</p>
          <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.9rem", fontWeight: 700 }}>{user.email || "— not provided —"}</p>
        </div>
        <div>
          <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, opacity: 0.7, marginBottom: "0.25rem" }}>MEMBER SINCE</p>
          <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.9rem", fontWeight: 700 }}>
            {new Date(user.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>
        {user.bio && (
          <div style={{ gridColumn: "1 / -1", borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
            <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, opacity: 0.7, marginBottom: "0.25rem" }}>BIOGRAPHICAL NOTE</p>
            <p style={{ fontStyle: "italic", fontSize: "1rem", lineHeight: 1.6 }}>{user.bio}</p>
          </div>
        )}
      </div>

      <div className="responsive-two-column">
        {/* Edit Profile */}
        <section className="trb-sidebar-card">
          <h2 className="trb-sidebar-heading">
            EDIT DOSSIER DETAILS
          </h2>
          <form onSubmit={handleSaveProfile} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }} htmlFor="profile-email">
                Email Address
              </label>
              <input
                id="profile-email"
                type="email"
                className="trb-input"
                style={{ width: "100%" }}
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="correspondent@example.com"
                disabled={profileSaving}
              />
            </div>
            <div>
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }} htmlFor="profile-bio">
                Biographical Note
              </label>
              <textarea
                id="profile-bio"
                className="trb-input"
                style={{ width: "100%", resize: "vertical" }}
                value={bio}
                onChange={e => setBio(e.target.value)}
                rows={4}
                placeholder="Write a brief introduction..."
                disabled={profileSaving}
              />
            </div>
            {profileMsg && (
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: profileMsg.startsWith("✓") ? "darkgreen" : "var(--accent-red)", fontWeight: 700 }}>
                {profileMsg}
              </p>
            )}
            <button type="submit" className="trb-btn-solid" disabled={profileSaving}>
              {profileSaving ? "SAVING..." : "SAVE DOSSIER"}
            </button>
          </form>
        </section>

        {/* Change Password */}
        <section className="trb-sidebar-card">
          <h2 className="trb-sidebar-heading">
            CHANGE PASSPHRASE
          </h2>
          <form onSubmit={handleChangePassword} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }} htmlFor="current-pwd">
                Current Passphrase
              </label>
              <input
                id="current-pwd"
                type="password"
                className="trb-input"
                style={{ width: "100%" }}
                value={currentPwd}
                onChange={e => setCurrentPwd(e.target.value)}
                required
                disabled={pwdSaving}
              />
            </div>
            <div>
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }} htmlFor="new-pwd">
                New Passphrase
              </label>
              <input
                id="new-pwd"
                type="password"
                className="trb-input"
                style={{ width: "100%" }}
                value={newPwd}
                onChange={e => setNewPwd(e.target.value)}
                required
                minLength={6}
                disabled={pwdSaving}
              />
            </div>
            <div>
              <label style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: 700, marginBottom: "0.35rem" }} htmlFor="confirm-pwd">
                Confirm New Passphrase
              </label>
              <input
                id="confirm-pwd"
                type="password"
                className="trb-input"
                style={{ width: "100%" }}
                value={confirmPwd}
                onChange={e => setConfirmPwd(e.target.value)}
                required
                disabled={pwdSaving}
              />
            </div>
            {pwdMsg && (
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: pwdMsg.startsWith("✓") ? "darkgreen" : "var(--accent-red)", fontWeight: 700 }}>
                {pwdMsg}
              </p>
            )}
            <button type="submit" className="trb-btn-solid" disabled={pwdSaving}>
              {pwdSaving ? "UPDATING..." : "UPDATE PASSPHRASE"}
            </button>
          </form>
        </section>
      </div>

      <div style={{ display: "flex", gap: "1rem", borderTop: "2px double var(--border-color)", paddingTop: "1.5rem", marginTop: "2.5rem" }}>
        <Link href="/" className="trb-btn-pill" style={{ textDecoration: "none" }}>
          RETURN TO FRONT PAGE
        </Link>
        <button onClick={handleLogout} className="trb-btn-pill" style={{ borderColor: "var(--accent-red)", color: "var(--accent-red)" }}>
          LOGOUT
        </button>
      </div>
    </div>
  );
}
