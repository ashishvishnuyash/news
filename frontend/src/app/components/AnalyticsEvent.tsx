"use client";

import { useEffect } from "react";
import { AnalyticsProperties, trackEvent } from "../../lib/analytics";

export default function AnalyticsEvent({ name, properties = {} }: { name: string; properties?: AnalyticsProperties }) {
  useEffect(() => { trackEvent(name, properties); }, [name, properties]);
  return null;
}
