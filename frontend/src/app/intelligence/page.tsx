"use client";

import { useCallback, useEffect, useState } from "react";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type Intelligence = { id: string; signal_id: string; title?: string; summary?: string; global_implication?: string; primary_domain?: string; urgency_band?: string; confidence_band?: string; source_name: string; source_url?: string; published_at?: string };
export default function IntelligencePage() {
  const [state, setState] = useState<LoadState<Intelligence[]>>({ status: "loading" });
  const load = useCallback(async () => { try { setState({ status: "ready", data: await apiRequest<Intelligence[]>("/api/v1/intelligence") }); } catch (error) { setState({ status: "error", message: error instanceof Error ? error.message : "Wider Intelligence could not be loaded." }); } }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  return <WorkspaceShell><section className="content-page"><div className="page-heading"><div><p className="eyebrow">Supporting market view</p><h1>Wider Intelligence</h1><p>Verified developments that do not currently require a Decision Brief.</p></div></div>
    {state.status === "loading" && <ModuleLoading />}{state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
    {state.status === "ready" && <div className="intelligence-list">{state.data.map((item) => <article key={item.id}><div className="brief-meta"><span>{item.primary_domain?.replaceAll("_", " ")}</span><span>{item.confidence_band} confidence</span></div><h2>{item.title || item.summary}</h2><p>{item.global_implication || item.summary}</p><footer><span>{item.source_name}</span>{item.source_url && <a href={item.source_url} rel="noreferrer" target="_blank">Open verified source</a>}</footer></article>)}{!state.data.length && <section className="empty-brief"><h2>No wider intelligence is available yet.</h2><p>The continuous signal pipeline is still monitoring approved Nigerian launch sources.</p></section>}</div>}
  </section></WorkspaceShell>;
}
