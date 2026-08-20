export type AnalyticsProperties = Record<string, string | number | boolean | null | undefined>;

declare global {
  interface Window { dataLayer?: Array<Record<string, unknown>> }
}

/** Emit non-PII editorial events for a configured analytics adapter. */
export function trackEvent(name: string, properties: AnalyticsProperties = {}) {
  if (typeof window === "undefined") return;
  const detail = { event: name, ...properties };
  window.dispatchEvent(new CustomEvent("trb:analytics", { detail }));
  if (Array.isArray(window.dataLayer)) window.dataLayer.push(detail);
}
