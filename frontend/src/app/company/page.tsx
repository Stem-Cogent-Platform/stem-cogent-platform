"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { BriefCard } from "@/components/brief-card";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { stateMessages } from "@/lib/product-copy/stateMessages";
import { Brief, LoadState } from "@/lib/types";

type Company = {
  profile: null | { business_categories: string[]; strategic_priorities: string[]; operating_markets: string[] };
  context_status: { complete: boolean; completeness: number; missing_fields: string[]; version: number };
  briefs: Brief[];
};

export default function CompanyPage() {
  const [state, setState] = useState<LoadState<Company>>({ status: "loading" });
  const [phase5Ui, setPhase5Ui] = useState(false);
  const load = useCallback(async () => { try { setState({ status: "loading" }); const [data, capabilities] = await Promise.all([apiRequest<Company>("/api/v1/company/briefs"), apiRequest<{ phase5_new_ui_enabled: boolean }>("/api/v1/capabilities")]); setPhase5Ui(capabilities.phase5_new_ui_enabled); setState({ status: "ready", data }); } catch (error) { setState({ status: "error", message: error instanceof Error ? error.message : "Company Lens could not be loaded." }); } }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  if (state.status === "ready" && !phase5Ui) {
    return <WorkspaceShell><section className="content-page"><div className="page-heading"><div><p className="eyebrow">Shared organisational view</p><h1>Company Lens</h1></div><Link className="secondary-button" href="/briefing">Switch to My Lens</Link></div><section className="company-summary"><div><small>Markets</small><strong>{state.data.profile?.operating_markets.join(", ") || "Context incomplete"}</strong></div><div><small>Strategic priorities</small><strong>{state.data.profile?.strategic_priorities.join(", ") || "Not configured"}</strong></div><div><small>Open material briefs</small><strong>{state.data.briefs.length}</strong></div></section><div className="card-list">{state.data.briefs.length ? state.data.briefs.map((brief) => <BriefCard brief={brief} key={brief.id} phase5Ui={false} />) : <section className="empty-brief"><h2>No company-level Decision Briefs are open.</h2><p>Stem will surface a brief when stored evidence and Company Context meet the materiality threshold.</p></section>}</div></section></WorkspaceShell>;
  }

  return <WorkspaceShell><section className="content-page"><div className="page-heading"><div><p className="eyebrow">Shared organisational view</p><h1>Company Lens</h1></div><Link className="secondary-button" href="/briefing">Switch to My Lens</Link></div>
    {state.status === "loading" && <ModuleLoading />}{state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
    {state.status === "ready" && <><section className="company-summary"><div><small>Company context</small><strong>{state.data.context_status.complete ? `${state.data.profile?.business_categories.join(", ") || "Configured"} · v${state.data.context_status.version}` : `${Math.round(state.data.context_status.completeness * 100)}% complete`}</strong></div><div><small>Operating markets</small><strong>{state.data.profile?.operating_markets.join(", ") || "Add market context"}</strong></div><div><small>Open material briefs</small><strong>{state.data.briefs.length}</strong></div></section><section className="panel priority-panel"><p className="eyebrow">Strategic priorities</p><div className="semantic-chips">{state.data.profile?.strategic_priorities.map((item) => <span key={item}>{item}</span>)}{!state.data.profile?.strategic_priorities.length && <p>Add priorities to improve company-level ranking.</p>}</div></section><section className="company-decisions"><div className="section-heading"><h2>Company decisions requiring attention</h2><span>{state.data.briefs.length} open</span></div><div className="card-list">{state.data.briefs.length ? state.data.briefs.map((brief) => <BriefCard brief={brief} key={brief.id} />) : <section className="empty-brief"><h2>{stateMessages.companyBriefsEmpty.title}</h2><p>{stateMessages.companyBriefsEmpty.body}</p></section>}</div></section></>}
  </section></WorkspaceShell>;
}
