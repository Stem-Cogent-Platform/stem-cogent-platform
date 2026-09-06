"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CILPanel } from "@/components/cil-panel";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type Evidence = { id: string; title?: string; source_name: string; source_url?: string; published_at?: string; detected_at?: string };
type Dossier = {
  signal: Evidence & { evidence_excerpt?: string; primary_domain?: string; confidence_band?: string; urgency_band?: string; summary?: string; global_implication?: string; confidence_note?: string; key_developments?: string[]; llm_synthesis_failed?: boolean; synthesized_at?: string };
  entities: { id: string; canonical_name: string; entity_type: string }[];
  evidence: Evidence[];
};
function date(value?: string) { return value ? new Date(value).toLocaleString() : "Not provided by the source"; }

export default function SignalPage() {
  const id = String(useParams<{ signalId: string }>().signalId ?? "");
  const [state, setState] = useState<LoadState<Dossier>>({ status: "loading" });
  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      setState({ status: "ready", data: await apiRequest<Dossier>(`/api/v1/signals/${id}`) });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "This signal is unavailable." });
    }
  }, [id]);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  return <WorkspaceShell><section className="content-page">
    <Link href="/intelligence">← Wider Intelligence</Link>
    {state.status === "loading" && <ModuleLoading label="Loading signal dossier" />}
    {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
    {state.status === "ready" && <>
      <div className="page-heading"><div><p className="eyebrow">Signal dossier</p><h1>{state.data.signal.title || "Source development"}</h1><p>{state.data.signal.primary_domain?.replaceAll("_", " ")}</p></div></div>
      <div className="detail-grid"><article className="brief-detail">
        <h2>What the evidence says</h2>
        {state.data.signal.llm_synthesis_failed && <p className="form-message">Automated analysis was unavailable for this record. The source evidence is retained below; this is not a completed analytical assessment.</p>}
        <p>{state.data.signal.summary || "A synthesized summary is not yet available. Review the source evidence below."}</p>
        {!state.data.signal.llm_synthesis_failed && state.data.signal.key_developments?.length ? <ul>{state.data.signal.key_developments.map((item, index) => <li key={index}>{item}</li>)}</ul> : null}
        {!state.data.signal.llm_synthesis_failed && state.data.signal.global_implication && <><h2>Market implication</h2><p>{state.data.signal.global_implication}</p></>}
        <h2>Evidence and timing</h2>
        <dl><dt>Published</dt><dd>{date(state.data.signal.published_at)}</dd><dt>First detected</dt><dd>{date(state.data.signal.detected_at)}</dd><dt>Analysis recorded</dt><dd>{date(state.data.signal.synthesized_at)}</dd><dt>Confidence</dt><dd>{state.data.signal.confidence_band?.replaceAll("_", " ").toLowerCase() || "Not assessed"}</dd></dl>
        {state.data.signal.confidence_note && <p>{state.data.signal.confidence_note}</p>}
        {state.data.signal.evidence_excerpt && <details><summary>Read stored source excerpt</summary><p>{state.data.signal.evidence_excerpt}</p></details>}
        <ul className="evidence-list">{state.data.evidence.map((item) => <li key={item.id}><div><strong>{item.title || item.source_name}</strong><small>{item.source_name} · Published: {date(item.published_at)}</small></div>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Open source</a>}</li>)}</ul>
        <h2>Related entities</h2>
        {state.data.entities.length ? <ul>{state.data.entities.map((entity) => <li key={entity.id}><Link href={`/entities/${entity.id}`}>{entity.canonical_name}</Link> · {entity.entity_type.replaceAll("_", " ")}</li>)}</ul> : <p>No supported entity links are available for this signal.</p>}
        <p>A signal dossier records evidence. A Decision Brief is created separately only when company relevance and decision thresholds are met.</p>
      </article><CILPanel anchorId={id} anchorType="SIGNAL" /></div>
    </>}
  </section></WorkspaceShell>;
}
