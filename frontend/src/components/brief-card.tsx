import Link from "next/link";

import { Brief } from "@/lib/types";

export function BriefCard({ brief }: { brief: Brief }) {
  return (
    <article className="brief-card">
      <div className="brief-meta">
        <span className={`priority-chip priority-${brief.relevance_band.toLowerCase()}`}>
          {brief.relevance_band}
        </span>
        <span>{brief.primary_domain?.replaceAll("_", " ") ?? "Decision intelligence"}</span>
        <span>{brief.confidence_band ?? "Evidence review"} confidence</span>
      </div>
      <h3>{brief.what_changed}</h3>
      {brief.why_it_matters && <p>{brief.why_it_matters}</p>}
      <dl className="brief-facts">
        <div><dt>Why shown</dt><dd>{brief.personal_priority_score ? `${Math.round(Number(brief.personal_priority_score) * 100)}% lens match` : "Company priority"}</dd></div>
        <div><dt>Evidence</dt><dd>{brief.evidence_signal_ids?.length ?? 0} source{brief.evidence_signal_ids?.length === 1 ? "" : "s"}</dd></div>
        <div><dt>Status</dt><dd>{brief.brief_status.replaceAll("_", " ")}</dd></div>
      </dl>
      <Link className="primary-link" href={`/briefs/${brief.id}`}>Open Decision Brief</Link>
    </article>
  );
}
