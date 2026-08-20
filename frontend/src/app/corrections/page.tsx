import type { Metadata } from "next";
import Link from "next/link";
import PageHeader from "../components/PageHeader";
import PublicShell from "../components/PublicShell";
import { formatNewsDate, getCorrections } from "../../lib/news";

export const metadata: Metadata = { title: "Corrections", description: "The Republic Bulletin correction record." };
export default async function CorrectionsPage() { const corrections = await getCorrections(); return <PublicShell><PageHeader eyebrow="Accountability" title="Corrections" description="A public record of material corrections made to published reporting." crumbs={[{ label: "Corrections" }]} /><div className="corrections-ledger">{corrections.length ? corrections.map((item) => <article key={item.id}><time dateTime={item.created_at}>{formatNewsDate(item.created_at, true)}</time><h2>{item.article_slug ? <Link href={`/articles/${item.article_slug}`}>{item.article_title}</Link> : item.article_title}</h2><p><strong>Correction:</strong> {item.summary}</p>{item.details && <p>{item.details}</p>}<span>Recorded by {item.recorded_by}</span></article>) : <section className="public-empty-state"><h2>No correction records</h2><p>No material corrections have been published in the correction ledger.</p></section>}</div></PublicShell>; }
