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

  useEffect(() => {
    Promise.all([
      apiFetch(apiUrl("/api/auth/me")).then((response) => response.ok ? response.json() : null),
      apiFetch(apiUrl("/api/users/me/notifications")).then((response) => response.ok ? response.json() : []),
    ]).then(([profile, items]) => { setUser(profile); setNotifications(items); });
  }, []);

  const markAllRead = async () => {
    const response = await apiFetch(apiUrl("/api/users/me/notifications/read-all"), { method: "PUT" });
    if (response.ok) setNotifications((items) => items.map((item) => ({ ...item, is_read: true })));
  };

  const unread = notifications.filter((item) => !item.is_read).length;

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
          {unread > 0 && <button className="trb-btn-pill" onClick={markAllRead}>Mark all read</button>}
        </div>
        {notifications.length === 0 ? (
          <p className="empty-copy">No notices yet. New activity will appear here.</p>
        ) : (
          <ol className="notice-list">
            {notifications.map((item) => (
              <li key={item.id} className={item.is_read ? "" : "is-unread"}>
                <span className="notice-dot" aria-label={item.is_read ? "Read" : "Unread"} />
                <div><p>{item.message}</p><time>{new Date(item.created_at).toLocaleString()}</time></div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
