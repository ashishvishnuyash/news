"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "../../lib/auth";
import { apiUrl, panelPathForRole } from "../../lib/config";
import type { SiteSettings, User } from "../../lib/types";

interface HeaderProps {
  currentCategory?: string;
  onCategoryChange?: (category: string) => void;
  onSearchChange?: (query: string) => void;
  activeDensity?: string;
  onDensityChange?: (density: string) => void;
  initialSettings?: SiteSettings;
}

const DEFAULT_SETTINGS: SiteSettings = {
  site_name: "The Republic Bulletin",
  site_motto: "Independent reporting for an informed republic",
  breaking_news: "",
  breaking_active: false,
  categories: ["Politics", "World", "Economy", "Technology", "Culture", "Opinion"],
};


const ROLE_LABEL: Record<string, string> = {
  READER: "Reader",
  JOURNALIST: "Journalist",
  EDITOR: "Editor",
  ADMIN: "Administrator",
  SUPER_ADMIN: "Publisher",
};

export default function Header({
  currentCategory = "All",
  onCategoryChange,
  onSearchChange,
  activeDensity = "broadsheet",
  onDensityChange,
  initialSettings,
}: HeaderProps) {
  const router = useRouter();
  const [theme, setTheme] = useState("parchment");
  const [fontSize, setFontSize] = useState("medium");
  const [user, setUser] = useState<User | null>(null);
  const [settings, setSettings] = useState<SiteSettings>(initialSettings || DEFAULT_SETTINGS);
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("trb_theme") || "parchment";
    const savedFont = window.localStorage.getItem("trb_font") || "medium";
    setTheme(savedTheme);
    setFontSize(savedFont);
    document.documentElement.dataset.theme = savedTheme;
    document.documentElement.dataset.fontSize = savedFont;

    Promise.allSettled([
      apiFetch(apiUrl("/api/auth/me")).then(async (response) => {
        setUser(response.ok ? await response.json() : null);
      }),
      fetch(apiUrl("/api/settings")).then(async (response) => {
        if (!response.ok) return;
        const data = await response.json();
        setSettings((previous) => ({ ...previous, ...data }));
      }),
    ]);
  }, []);

  const categories = useMemo(() => {
    const unique = settings.categories.filter((item, index, list) => item && list.indexOf(item) === index);
    return ["All", ...unique];
  }, [settings.categories]);

  const changeTheme = (value: string) => {
    setTheme(value);
    window.localStorage.setItem("trb_theme", value);
    document.documentElement.dataset.theme = value;
  };

  const changeFontSize = (value: string) => {
    setFontSize(value);
    window.localStorage.setItem("trb_font", value);
    document.documentElement.dataset.fontSize = value;
  };

  const logout = async () => {
    await apiFetch(apiUrl("/api/auth/logout"), { method: "POST" }).catch(() => undefined);
    window.localStorage.removeItem("chronicle_token");
    setUser(null);
    router.push("/");
    router.refresh();
  };

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = query.trim();
    if (onSearchChange) onSearchChange(normalized);
    else router.push(`/search${normalized ? `?q=${encodeURIComponent(normalized)}` : ""}`);
  };

  const currentDate = new Intl.DateTimeFormat("en-IN", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date());
  const mastheadName = settings.site_name.replace(/^the\s+/i, "").trim() || settings.site_name;

  return (
    <header className="site-header" id="masthead">
      <a className="skip-link" href="#main-content">Skip to the news</a>

      <div className="utility-bar">
        <p className="utility-edition">Morning edition · {currentDate}</p>
        <button
          className="mobile-menu-button"
          type="button"
          aria-expanded={menuOpen}
          aria-controls="reader-tools"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? "Close" : "Reader tools"}
        </button>
        <div className={`reader-tools ${menuOpen ? "is-open" : ""}`} id="reader-tools">
          {onDensityChange && (
            <div className="segmented-control" aria-label="Story layout">
              {["broadsheet", "tabloid", "single"].map((value) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={activeDensity === value}
                  onClick={() => onDensityChange(value)}
                >
                  {value === "single" ? "Focus" : value}
                </button>
              ))}
            </div>
          )}
          <label className="compact-label">
            Paper
            <select value={theme} onChange={(event) => changeTheme(event.target.value)}>
              <option value="parchment">Newsprint</option>
              <option value="white">White</option>
              <option value="dark">Night</option>
            </select>
          </label>
          <div className="segmented-control" aria-label="Text size">
            {["small", "medium", "large"].map((value, index) => (
              <button
                key={value}
                type="button"
                aria-label={`${value} text`}
                aria-pressed={fontSize === value}
                onClick={() => changeFontSize(value)}
              >
                {index === 0 ? "A−" : index === 1 ? "A" : "A+"}
              </button>
            ))}
          </div>
          <button className="text-button" type="button" onClick={() => window.print()}>Print edition</button>
          <div className="account-actions" id="account-controls">
            {user ? (
              <>
                <Link href={panelPathForRole(user.role)} className="account-link">
                  {user.username} · {ROLE_LABEL[user.role] || user.role}
                </Link>
                <Link href="/profile" className="text-button">Profile</Link>
                <button className="text-button" type="button" onClick={logout}>Sign out</button>
              </>
            ) : (
              <>
                <Link href="/login" className="text-button">Sign in</Link>
                <Link href="/register" className="button button-dark">Subscribe free</Link>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="masthead-lockup">
        <Link href="/" className="masthead-link" aria-label={`${settings.site_name} home`}>

          <span className="masthead-crown" aria-hidden="true">
            <span className="masthead-rule" />
            <span className="masthead-the">The</span>
            <span className="masthead-rule" />
          </span>
          <span className="masthead-name">{mastheadName}</span>
          <span className="masthead-main-rule" aria-hidden="true" />
        </Link>
        <div className="masthead-motto-row">
          <span className="motto-rule" aria-hidden="true" />
          <p className="masthead-motto">{settings.site_motto}</p>
          <span className="motto-rule" aria-hidden="true" />
        </div>
      </div>

      {settings.breaking_active && settings.breaking_news && (
        <div className="breaking-strip" role="status">
          <strong>Breaking</strong><span>{settings.breaking_news}</span>
        </div>
      )}

      <div className="section-bar" id="category-bar">
        <nav aria-label="News sections" className="section-nav">
          {categories.map((category) => (
            onCategoryChange ? (
              <button
                key={category}
                type="button"
                className={currentCategory.toLowerCase() === category.toLowerCase() ? "is-active" : ""}
                aria-pressed={currentCategory.toLowerCase() === category.toLowerCase()}
                onClick={() => onCategoryChange(category)}
              >
                {category}
              </button>
            ) : (
              <Link
                key={category}
                href={category === "All" ? "/" : `/section/${encodeURIComponent(category.toLowerCase())}`}
                className={currentCategory.toLowerCase() === category.toLowerCase() ? "is-active" : ""}
                aria-current={currentCategory.toLowerCase() === category.toLowerCase() ? "page" : undefined}
              >
                {category}
              </Link>
            )
          ))}
        </nav>
        <form className="archive-search" role="search" onSubmit={submitSearch}>
          <label className="sr-only" htmlFor="archive-query">Search stories</label>
          <input
            id="archive-query"
            type="search"
            placeholder="Search the archive"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="submit" aria-label="Search">Search</button>
        </form>
      </div>
    </header>
  );
}
