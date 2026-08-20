import type { SiteSettings } from "../../lib/types";

type Slot = "header" | "homepage" | "in_feed" | "article" | "sidebar" | "footer";

export default function AdSlot({ slot, settings }: { slot: Slot; settings: SiteSettings }) {
  const content = settings.advertising?.slots?.[slot];
  if (!settings.advertising?.enabled || !content) return null;
  return (
    <aside className={`ad-slot ad-slot-${slot}`} aria-label="Advertisement">
      <span>Advertisement</span>
      <div>{content}</div>
    </aside>
  );
}
