import Image from "next/image";
import Link from "next/link";
import { articleHref, articlePreview, authorHref, formatNewsDate } from "../../lib/news";
import type { Article } from "../../lib/types";

export default function ArticleCard({ article, compact = false }: { article: Article; compact?: boolean }) {
  return (
    <article className={`editorial-card ${compact ? "is-compact" : ""}`}>
      {!compact && article.image_url && (
        <Link href={articleHref(article)} className="editorial-card-image">
          <Image src={article.image_url} alt={article.image_caption || article.title} width={720} height={430} />
        </Link>
      )}
      <div className="editorial-card-copy">
        <p className="story-kicker">{article.category}{article.fact_check_rating ? ` · ${article.fact_check_rating.replace("_", " ")}` : ""}</p>
        <h3><Link href={articleHref(article)}>{article.title}</Link></h3>
        {!compact && <p>{articlePreview(article)}</p>}
        <div className="story-byline">
          <span>By <Link href={authorHref(article.author)}>{article.author.username}</Link></span>
          <time dateTime={article.published_at || article.created_at}>{formatNewsDate(article.published_at || article.created_at)}</time>
        </div>
      </div>
    </article>
  );
}
