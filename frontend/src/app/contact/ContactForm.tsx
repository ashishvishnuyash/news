"use client";

import { FormEvent, useState } from "react";
import { apiUrl } from "../../lib/config";
import { trackEvent } from "../../lib/analytics";

const PURPOSES = [
  ["general", "General"],
  ["tips", "News tip"],
  ["corrections", "Correction"],
  ["advertising", "Advertising"],
  ["press", "Press"],
] as const;

export default function ContactForm() {
  const [purpose, setPurpose] = useState("general");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [state, setState] = useState<"idle" | "saving" | "success" | "error">("idle");
  const [notice, setNotice] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setState("saving");
    setNotice("");
    try {
      const response = await fetch(apiUrl("/api/newsroom/messages"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ purpose, name: name.trim() || null, email: email.trim() || null, message }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail : "Your message could not be saved.");
      }
      setState("success");
      setNotice("Your message has been recorded for the newsroom.");
      setMessage("");
      trackEvent("newsroom_message", { purpose });
    } catch (error) {
      setState("error");
      setNotice(error instanceof Error ? error.message : "Your message could not be saved.");
    }
  }

  return (
    <section className="policy-page newsroom-contact-form" aria-labelledby="newsroom-message-heading">
      <h2 id="newsroom-message-heading">Send a newsroom message</h2>
      <p className="configuration-note">This standard web form is not an anonymous or end-to-end encrypted tip channel. Avoid sending sensitive identifying information.</p>
      <form className="crud-form" onSubmit={submit}>
        <div className="crud-form-grid">
          <label>Purpose<select value={purpose} onChange={(event) => setPurpose(event.target.value)}>{PURPOSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label>Name (optional)<input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} autoComplete="name" /></label>
          <label>Email (optional)<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} maxLength={254} autoComplete="email" /></label>
          <label className="crud-wide">Message<textarea required minLength={20} maxLength={10000} rows={8} value={message} onChange={(event) => setMessage(event.target.value)} /></label>
        </div>
        <button className="trb-btn-solid" disabled={state === "saving"}>{state === "saving" ? "Sending…" : "Send to newsroom"}</button>
        {notice && <p className={`crud-notice ${state === "error" ? "error" : "success"}`} role="status">{notice}</p>}
      </form>
    </section>
  );
}
