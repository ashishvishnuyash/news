"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiFetch } from "../../lib/auth";
import { apiUrl, panelUrlForRole, siteUrl } from "../../lib/config";
import type { Role, User } from "../../lib/types";

const PANEL_META: Array<{ role: Role; label: string; description: string }> = [
  { role: "SUPER_ADMIN", label: "Publisher", description: "Publication settings" },
  { role: "ADMIN", label: "Administration", description: "People and operations" },
  { role: "EDITOR", label: "Editorial", description: "Review and publish" },
  { role: "JOURNALIST", label: "Newsroom", description: "Draft and submit" },
  { role: "READER", label: "Reader", description: "Account overview" },
];

const ACCESS: Record<Role, Role[]> = {
  SUPER_ADMIN: ["SUPER_ADMIN", "ADMIN", "EDITOR", "JOURNALIST", "READER"],
  ADMIN: ["ADMIN", "EDITOR", "JOURNALIST", "READER"],
  EDITOR: ["EDITOR", "READER"],
  JOURNALIST: ["JOURNALIST", "READER"],
  READER: ["READER"],
};

function roleForPath(pathname: string): Role {
  if (pathname.includes("/superadmin")) return "SUPER_ADMIN";
  if (pathname.includes("/admin")) return "ADMIN";
  if (pathname.includes("/editor")) return "EDITOR";
  if (pathname.includes("/journalist")) return "JOURNALIST";
  return "READER";
}

export default function PanelsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const expectedRole = useMemo(() => roleForPath(pathname), [pathname]);
  const [user, setUser] = useState<User | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "denied" | "error">("loading");

  useEffect(() => {
    let active = true;
    setState("loading");
    apiFetch(apiUrl("/api/auth/me"))
      .then(async (response) => {
        if (!active) return;
        if (response.status === 401 || response.status === 403) {
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
          return;
        }
        if (!response.ok) throw new Error(`Authentication failed (${response.status})`);
        const currentUser: User = await response.json();
        setUser(currentUser);
        setState(ACCESS[currentUser.role]?.includes(expectedRole) ? "ready" : "denied");
      })
      .catch(() => active && setState("error"));
    return () => { active = false; };
  }, [expectedRole, pathname, router]);

  const logout = async () => {
    await apiFetch(apiUrl("/api/auth/logout"), { method: "POST" }).catch(() => undefined);
    window.localStorage.removeItem("chronicle_token");
    window.location.href = siteUrl("/login");
  };

  if (state === "loading") {
    return <div className="panel-state"><span className="loading-rule" />Verifying newsroom credentials…</div>;
  }

  if (state === "error") {
    return (
      <div className="panel-state-card" role="alert">
        <p className="eyebrow">Pressroom unavailable</p>
        <h1>We could not reach the newsroom server.</h1>
        <p>Check the API connection, then try again. Your work has not been changed.</p>
        <button className="trb-btn-solid" onClick={() => window.location.reload()}>Try again</button>
      </div>
    );
  }

  if (state === "denied") {
    return (
      <div className="panel-state-card" role="alert">
        <p className="eyebrow">Access restricted</p>
        <h1>This desk requires {expectedRole.replace("_", " ")} credentials.</h1>
        <p>You are signed in as {user?.role.replace("_", " ")}. Choose one of your available desks instead.</p>
        <a className="trb-btn-solid" href={panelUrlForRole(user?.role || "READER")}>Open my desk</a>
      </div>
    );
  }

  const desks = user ? PANEL_META.filter((item) => ACCESS[user.role].includes(item.role)) : [];
  const activeDesk = PANEL_META.find((item) => item.role === expectedRole);

  return (
    <div className="panel-shell">
      <header className="panel-header">
        <div className="panel-header-top">
          <a href={siteUrl("/")} className="panel-wordmark">The Republic Bulletin</a>
          <div className="panel-user">
            <span>{user?.username}</span>
            <span className="role-chip">{user?.role.replace("_", " ")}</span>
            <a href={siteUrl("/profile")}>Profile</a>
            <button type="button" onClick={logout}>Sign out</button>
          </div>
        </div>
        <div className="panel-title-row">
          <div>
            <p className="eyebrow">Confidential staff edition</p>
            <h1>{activeDesk?.label || "Newsroom"} desk</h1>
            <p>{activeDesk?.description}</p>
          </div>
          <a href={siteUrl("/")} className="trb-btn-pill">View front page</a>
        </div>
        <nav className="panel-nav" aria-label="Available staff desks">
          {desks.map((desk) => (
            <a
              key={desk.role}
              href={panelUrlForRole(desk.role)}
              aria-current={desk.role === expectedRole ? "page" : undefined}
            >
              {desk.label}
            </a>
          ))}
        </nav>
      </header>
      <main className="panel-content" id="main-content">{children}</main>
      <footer className="panel-footer">
        <strong>The Republic Bulletin · Staff Pressroom</strong>
        <span>Role-protected publishing operations</span>
      </footer>
    </div>
  );
}
