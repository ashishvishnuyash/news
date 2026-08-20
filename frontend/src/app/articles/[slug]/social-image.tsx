/* eslint-disable @next/next/no-img-element -- ImageResponse requires a raw img for in-memory cover data. */
import { ImageResponse } from "next/og";
import { apiUrl } from "../../../lib/config";

type SocialArticle = {
  title: string;
  summary?: string | null;
  category?: string | null;
  image_url?: string | null;
  og_image_url?: string | null;
  author?: { username?: string | null } | null;
};

export const socialImageSize = { width: 1200, height: 630 };

async function getArticle(slug: string): Promise<SocialArticle | null> {
  try {
    const response = await fetch(apiUrl(`/api/articles/${encodeURIComponent(slug)}?track_view=false`), {
      next: { revalidate: 60 },
    });
    return response.ok ? response.json() : null;
  } catch {
    return null;
  }
}

async function getCover(url?: string | null): Promise<ArrayBuffer | null> {
  if (!url) return null;
  try {
    const resolved = /^https?:\/\//i.test(url) ? url : apiUrl(url);
    const response = await fetch(resolved, { next: { revalidate: 3600 } });
    return response.ok ? response.arrayBuffer() : null;
  } catch {
    return null;
  }
}

export async function createArticleSocialImage(slug: string) {
  const article = await getArticle(slug);
  const cover = await getCover(article?.og_image_url || article?.image_url);
  const title = article?.title || "The Republic Bulletin";
  const summary = article?.summary?.trim() || "Independent reporting for the public record.";

  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", background: "#f3eedf", color: "#171512", padding: "44px", gap: "38px" }}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "space-between", border: "5px double #171512", padding: "34px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            <div style={{ display: "flex", fontSize: 24, letterSpacing: 4, textTransform: "uppercase", color: "#8d1d17" }}>
              {article?.category || "Latest dispatch"}
            </div>
            <div style={{ display: "flex", fontFamily: "serif", fontSize: title.length > 75 ? 48 : 58, fontWeight: 800, lineHeight: 1.02 }}>
              {title}
            </div>
            <div style={{ display: "flex", fontSize: 25, lineHeight: 1.35, opacity: 0.82 }}>
              {summary.length > 170 ? `${summary.slice(0, 167)}…` : summary}
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", borderTop: "3px solid #171512", paddingTop: "18px", fontSize: 22, textTransform: "uppercase", letterSpacing: 2 }}>
            <span>The Republic Bulletin</span>
            <span>{article?.author?.username ? `By ${article.author.username}` : "Public record"}</span>
          </div>
        </div>
        {cover && (
          <div style={{ width: "42%", display: "flex", border: "5px solid #171512", overflow: "hidden" }}>
            {/* @ts-expect-error ImageResponse supports ArrayBuffer image sources. */}
            <img src={cover} alt="" width="100%" height="100%" style={{ objectFit: "cover" }} />
          </div>
        )}
      </div>
    ),
    socialImageSize,
  );
}
