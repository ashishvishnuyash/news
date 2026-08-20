"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "../../../lib/auth";
import { apiUrl } from "../../../lib/config";
import type { User } from "../../../lib/types";

interface Notification {
  id: number;
  message: string;
  type: string;
  is_read: boolean;
  link?: string | null;
  created_at: string;
}

export default function UserPanel() {
  const [user, setUser] = useState<User | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadDashboard = async () => {
    setLoading(true);
    await Promise.all([
      apiFetch(apiUrl("/api/auth/me")).then((response) => response.ok ? response.json() : null),
      apiFetch(apiUrl("/api/users/me/notifications")).then((response) => response.ok ? response.json() : []),
    ]).then(([profile, items]) => { setUser(profile); setNotifications(items); })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    void loadDashboard();
  }, []);

  const markAllRead = async () => {
    const response = await apiFetch(apiUrl("/api/users/me/notifications/read-all"), { method: "PUT" });
    if (response.ok) setNotifications((items) => items.map((item) => ({ ...item, is_read: true })));
  };

  const unread = notifications.filter((item) => !item.is_read).length;
  const visibleNotifications = showUnreadOnly ? notifications.filter((item) => !item.is_read) : notifications;

  const markRead = async (notificationId: number) => {
    const response = await apiFetch(apiUrl(`/api/users/me/notifications/${notificationId}/read`), { method: "PUT" });
    if (response.ok) setNotifications((items) => items.map((item) => item.id === notificationId ? { ...item, is_read: true } : item));
  };

  return (
    <div className="reader-dashboard">
      <section className="reader-welcome">
        <p className="eyebrow">Reader account</p>
        <h2>Good day, {user?.username || "reader"}.</h2>
        <p>Your subscription desk keeps account details and newsroom notices in one place.</p>
        <div className="reader-actions">
          <Link href="/profile" className="trb-btn-solid">Edit profile & password</Link>
          <Link href="/" className="trb-btn-pill">Read today’s edition</Link>
        </div>
      </section>
      <section className="trb-sidebar-card">
        <div className="notice-heading">
          <div><p className="eyebrow">Newsroom wire</p><h3>Notifications</h3></div>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button className="trb-btn-pill" onClick={() => setShowUnreadOnly((value) => !value)} aria-pressed={showUnreadOnly}>{showUnreadOnly ? "Show all" : `Unread (${unread})`}</button>
            <button className="trb-btn-pill" onClick={() => void loadDashboard()} disabled={loading}>Refresh</button>
            {unread > 0 && <button className="trb-btn-pill" onClick={markAllRead}>Mark all read</button>}
          </div>
        </div>
        {loading ? (
          <p className="empty-copy">Loading newsroom notices…</p>
        ) : visibleNotifications.length === 0 ? (
          <p className="empty-copy">{showUnreadOnly ? "You have no unread notices." : "No notices yet. New activity will appear here."}</p>
        ) : (
          <ol className="notice-list">
            {visibleNotifications.map((item) => (
              <li key={item.id} className={item.is_read ? "" : "is-unread"}>
                <span className="notice-dot" aria-label={item.is_read ? "Read" : "Unread"} />
                <div>
                  <p>{item.message}</p>
                  <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
                    <time>{new Date(item.created_at).toLocaleString()}</time>
                    {item.link && <Link href={item.link} onClick={() => void markRead(item.id)}>Open notice</Link>}
                    {!item.is_read && <button type="button" onClick={() => void markRead(item.id)}>Mark read</button>}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
