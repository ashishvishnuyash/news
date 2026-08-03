"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiErrorMessage } from "../../lib/auth";
import { apiUrl } from "../../lib/config";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [complete, setComplete] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    if (password !== confirmation) return setError("The passwords do not match.");
    if (password.length < 8) return setError("Use at least 8 characters for your password.");
    setLoading(true);
    try {
      const response = await fetch(apiUrl("/api/auth/register"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), email: email.trim() || null, password, confirm_password: confirmation }),
      });
      if (!response.ok) {
        setError(await apiErrorMessage(response, "Registration could not be completed."));
        return;
      }
      const login = await fetch(apiUrl("/api/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username: username.trim(), password }),
      });
      if (!login.ok) throw new Error("Account created, but sign-in failed");
      setComplete(true);
      window.setTimeout(() => window.location.assign("/panels/user"), 900);
    } catch {
      setError("The newsroom server is unavailable. Please try again in a moment.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-intro" aria-labelledby="register-title">
        <Link href="/" className="auth-wordmark">The Republic Bulletin</Link>
        <p className="eyebrow">Free reader account</p>
        <h1 id="register-title">Join the conversation around the day’s news.</h1>
        <p>Your account starts as a reader. Publication administrators assign newsroom roles separately.</p>
        <ul className="auth-benefits">
          <li>Comment on published reporting</li>
          <li>Keep a personal reader profile</li>
          <li>Receive newsroom notifications</li>
        </ul>
      </section>
      <section className="auth-card">
        <p className="auth-folio">Subscriber ledger · Form 02</p>
        <h2>{complete ? "Account created" : "Create account"}</h2>
        {complete ? (
          <div className="success-notice" role="status">Your account is ready. Opening your reader desk…</div>
        ) : (
          <>
            {error && <div className="form-alert" role="alert">{error}</div>}
            <form onSubmit={submit} className="stack-form">
              <label>Username<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} pattern="[A-Za-z0-9_.-]{3,40}" title="3–40 letters, numbers, dots, dashes, or underscores" required disabled={loading} /></label>
              <label>Email <span>(optional)</span><input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} disabled={loading} /></label>
              <label>Password<input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} maxLength={128} required disabled={loading} /></label>
              <label>Confirm password<input type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} minLength={8} required disabled={loading} /></label>
              <button className="button button-dark auth-submit" type="submit" disabled={loading}>{loading ? "Creating account…" : "Create reader account"}</button>
            </form>
          </>
        )}
        <div className="auth-links"><Link href="/">Front page</Link><Link href="/login">Already registered?</Link></div>
      </section>
    </main>
  );
}
