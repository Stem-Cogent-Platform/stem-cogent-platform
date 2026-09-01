"use client";

import Link from "next/link";
import { useState } from "react";

import { apiRequest } from "@/lib/api";
import { Brief } from "@/lib/types";

function age(value?: string) {
  if (!value) return "Recently";
  const hours = Math.max(1, Math.round((Date.now() - new Date(value).getTime()) / 3_600_000));
  return hours < 24 ? `${hours}h` : `${Math.round(hours / 24)}d`;
}

export function BriefCard({ brief }: { brief: Brief }) {
  const [watching, setWatching] = useState(brief.brief_status === "WATCHING");
  const [pending, setPending] = useState(false);
  const priority = brief.urgency_band ?? brief.relevance_band;
  const updated = Number(brief.material_change_count ?? 0) > 0;

  async function watch() {
    if (pending || watching) return;
    setPending(true);
    try {
      await apiRequest(`/api/v1/briefs/${brief.id}/actions`, { method: "POST", body: JSON.stringify({ action_type: "WATCHING" }) });
      setWatching(true);
    } finally {
      setPending(false);
    }
  }

  return <article className={`brief-card urgency-${priority.toLowerCase()}`}>
    <div className="brief-meta"><span className={`priority-chip priority-${brief.relevance_band.toLowerCase()}`}>{brief.relevance_band}</span><span>{brief.primary_domain?.replaceAll("_", " ") ?? "Decision intelligence"}</span>{updated && <span className="updated-chip">Updated</span>}<time dateTime={brief.last_material_change_at ?? brief.created_at}>{age(brief.last_material_change_at ?? brief.created_at)}</time></div>
    <h3>{brief.what_changed}</h3>{brief.why_it_matters && <p>{brief.why_it_matters}</p>}
    <div className="brief-chip-row">{brief.exposure_types?.slice(0, 3).map((item) => <span key={item}>{item.replaceAll("_", " ")}</span>)}{brief.stakes_types?.slice(0, 2).map((item) => <span className="stakes-chip" key={item}>{item.replaceAll("_", " ")}</span>)}</div>
    {brief.decision_prompt && <blockquote><span>Decision</span>{brief.decision_prompt}</blockquote>}
    <dl className="brief-facts"><div><dt>Owner</dt><dd>{brief.owner_roles?.join(", ") || "Leadership"}</dd></div><div><dt>Window</dt><dd>{brief.decision_window || "Monitor"}</dd></div><div><dt>Confidence</dt><dd>{brief.confidence_band ?? "Reviewed"}</dd></div><div><dt>Evidence</dt><dd>{brief.evidence_signal_ids?.length ?? 0} item{brief.evidence_signal_ids?.length === 1 ? "" : "s"}</dd></div></dl>
    <footer className="brief-card-actions"><Link className="primary-button" href={`/briefs/${brief.id}`}>Open brief</Link><button className="secondary-button" disabled={pending || watching} onClick={() => void watch()} type="button">{pending ? "Saving..." : watching ? "Watching" : "Watch"}</button></footer>
  </article>;
}
