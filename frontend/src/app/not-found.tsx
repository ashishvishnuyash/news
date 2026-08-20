import Link from "next/link";
import PublicShell from "./components/PublicShell";

export default function NotFound() {
  return <PublicShell><section className="public-empty-state"><p className="eyebrow">404 · Archive notice</p><h1>That page is not in this edition</h1><p>The story may have moved, or the address may be incomplete.</p><div><Link className="trb-btn-solid" href="/">Return home</Link> <Link className="trb-btn-pill" href="/search">Search the archive</Link></div></section></PublicShell>;
}
