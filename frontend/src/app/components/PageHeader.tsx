import Link from "next/link";

export default function PageHeader({
  eyebrow,
  title,
  description,
  crumbs = [],
}: {
  eyebrow: string;
  title: string;
  description?: string;
  crumbs?: Array<{ label: string; href?: string }>;
}) {
  return (
    <header className="editorial-page-header">
      {crumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="breadcrumbs">
          <Link href="/">Home</Link>
          {crumbs.map((crumb) => <span key={crumb.label}>{crumb.href ? <Link href={crumb.href}>{crumb.label}</Link> : crumb.label}</span>)}
        </nav>
      )}
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      {description && <p>{description}</p>}
    </header>
  );
}
