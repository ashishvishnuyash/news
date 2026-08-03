"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiErrorMessage } from "../../lib/auth";
import { apiUrl, panelPathForRole } from "../../lib/config";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await fetch(apiUrl("/api/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username: username.trim(), password }),
      });
      if (!response.ok) {
        setError(await apiErrorMessage(response, "The username or password is incorrect."));
        return;
      }
      const data = await response.json();
      window.localStorage.removeItem("chronicle_token");
      const next = new URLSearchParams(window.location.search).get("next");
      const safeNext = next?.startsWith("/") && !next.startsWith("//") ? next : panelPathForRole(data.user?.role || "READER");
      window.location.assign(safeNext);
    } catch {
      setError("The newsroom server is unavailable. Please try again in a moment.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-intro" aria-labelledby="login-title">
        <Link href="/" className="auth-wordmark">The Republic Bulletin</Link>
        <p className="eyebrow">Subscriber & staff access</p>
        <h1 id="login-title">Welcome back to the daily record.</h1>
        <p>Sign in to comment, manage your profile, or return to your newsroom desk.</p>
        <blockquote>“A free press needs careful readers and fearless reporters.”</blockquote>
      </section>
      <section className="auth-card">
        <p className="auth-folio">Credential ledger · Form 01</p>
        <h2>Sign in</h2>
        {error && <div className="form-alert" role="alert">{error}</div>}
        <form onSubmit={submit} className="stack-form">
          <label>
            Username
            <input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} minLength={3} required disabled={loading} />
          </label>
          <label>
            Password
            <input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required disabled={loading} />
          </label>
          <button className="button button-dark auth-submit" type="submit" disabled={loading}>
            {loading ? "Checking credentials…" : "Enter the pressroom"}
          </button>
        </form>
        <div className="auth-links">
          <Link href="/">Return to front page</Link>
          <Link href="/register">Create an account</Link>
        </div>
      </section>
    </main>
  );
}
