import Link from "next/link";

import { StemMark } from "@/components/stem-mark";

export function LegalDocumentPage({
  title,
  version,
  sections
}: {
  title: string;
  version: string;
  sections: readonly (readonly [string, string])[];
}) {
  return (
    <main className="legal-page">
      <header className="site-header">
        <Link className="wordmark" href="/"><StemMark /><span>Stem</span></Link>
        <Link className="text-link" href="/">Return to consent</Link>
      </header>
      <article className="legal-document">
        <p className="eyebrow">Effective version {version}</p>
        <h1>{title}</h1>
        <p className="legal-lead">This document is version controlled. Material changes require a new recorded acceptance.</p>
        {sections.map(([heading, content]) => (
          <section key={heading}>
            <h2>{heading}</h2>
            <p>{content}</p>
          </section>
        ))}
      </article>
    </main>
  );
}
