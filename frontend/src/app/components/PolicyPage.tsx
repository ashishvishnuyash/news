import PageHeader from "./PageHeader";
import PublicShell from "./PublicShell";

export default function PolicyPage({
  eyebrow,
  title,
  description,
  sections,
}: {
  eyebrow: string;
  title: string;
  description: string;
  sections: Array<{ title: string; content: React.ReactNode }>;
}) {
  return (
    <PublicShell>
      <PageHeader eyebrow={eyebrow} title={title} description={description} crumbs={[{ label: title }]} />
      <article className="policy-page">
        {sections.map((section) => <section key={section.title}><h2>{section.title}</h2><div>{section.content}</div></section>)}
      </article>
    </PublicShell>
  );
}
