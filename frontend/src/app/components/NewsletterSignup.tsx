"use client";

import { FormEvent, useState } from "react";
import { apiUrl } from "../../lib/config";
import { trackEvent } from "../../lib/analytics";

export default function NewsletterSignup({
  name = "The Republic Brief",
  description = "The biggest stories you need to know, delivered without the noise.",
  source = "website",
}: {
  name?: string;
  description?: string;
  source?: string;
}) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setState("loading");
    setMessage("");
    try {
      const response = await fetch(apiUrl("/api/newsletter/subscribe"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Subscription could not be saved.");
      setState("success");
      setMessage(data?.message || "Subscription saved.");
      setEmail("");
      trackEvent("newsletter_signup", { source });
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Subscription could not be saved.");
    }
  };

  return (
    <section className="newsletter-cta" aria-labelledby={`newsletter-${source}`}>
      <div>
        <p className="eyebrow">Newsletter</p>
        <h2 id={`newsletter-${source}`}>{name}</h2>
        <p>{description}</p>
      </div>
      <form onSubmit={submit}>
        <label htmlFor={`newsletter-email-${source}`}>Email address</label>
        <div>
          <input id={`newsletter-email-${source}`} type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required placeholder="you@example.com" />
          <button className="trb-btn-solid" disabled={state === "loading"}>{state === "loading" ? "Subscribing…" : "Subscribe"}</button>
        </div>
        {message && <p className={`newsletter-message ${state}`} role="status">{message}</p>}
      </form>
    </section>
  );
}
