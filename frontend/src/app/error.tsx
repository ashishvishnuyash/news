"use client";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return <main id="main-content" className="public-empty-state"><p className="eyebrow">Newsroom error</p><h1>This page could not be assembled</h1><p>The public record has not been changed. Try loading it again.</p><button className="trb-btn-solid" onClick={reset}>Try again</button></main>;
}
