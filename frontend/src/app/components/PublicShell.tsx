import Link from "next/link";
import Header from "./Header";
import AdSlot from "./AdSlot";
import { getSiteSettings } from "../../lib/news";

export default async function PublicShell({
  children,
  currentCategory = "All",
}: {
  children: React.ReactNode;
  currentCategory?: string;
}) {
  const settings = await getSiteSettings();
  const publicationName = settings.publication?.legal_name || settings.site_name;

  return (
    <div className="trb-container public-shell">
      <Header currentCategory={currentCategory} initialSettings={settings} />
      <main id="main-content" className="public-main">{children}</main>
      <footer className="public-footer">
        <AdSlot slot="footer" settings={settings} />
        <div className="public-footer-grid">
          <div>
            <h2>{settings.site_name}</h2>
            <p>{settings.site_motto}</p>
          </div>
          <nav aria-label="Publication information">
            <Link href="/about">About</Link>
            <Link href="/editorial-standards">Editorial standards</Link>
            <Link href="/corrections">Corrections</Link>
            <Link href="/contact">Contact</Link>
            <Link href="/privacy">Privacy</Link>
            <Link href="/terms">Terms</Link>
            <Link href="/copyright">Copyright</Link>
            <Link href="/advertising">Advertising</Link>
          </nav>
        </div>
        <div className="public-footer-meta">
          <span>{publicationName}</span>
          <span>Independent reporting for the public record</span>
        </div>
      </footer>
    </div>
  );
}
