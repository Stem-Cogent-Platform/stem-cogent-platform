"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { BriefCard } from "@/components/brief-card";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { stateMessages } from "@/lib/product-copy/stateMessages";
import { Brief, LoadState } from "@/lib/types";

type Company = { profile: null | { company_type?: string; headquarters_country?: string; strategic_priorities: string[]; operating_markets: string[] }; briefs: Brief[] };

export default function CompanyPage() {
  const [state, setState] = useState<LoadState<Company>>({ status: "loading" });
  const load = useCallback(async () => { try { setState({ status: "loading" }); setState({ status: "ready", data: await apiRequest<Company>("/api/v1/company/briefs") }); } catch (error) { setState({ status: "error", message: error instanceof Error ? error.message : "Company Lens could not be loaded." }); } }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  return <WorkspaceShell><section className="content-page"><div className="page-heading"><div><p className="eyebrow">Shared organisational view</p><h1>Company Lens</h1></div><Link className="secondary-button" href="/briefing">Switch to My Lens</Link></div>
    {state.status === "loading" && <ModuleLoading />}{state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
    {state.status === "ready" && <><section className="company-summary"><div><small>Company context</small><strong>{[state.data.profile?.company_type, state.data.profile?.headquarters_country].filter(Boolean).join(" · ") || "Setup needed"}</strong></div><div><small>Operating markets</small><strong>{state.data.profile?.operating_markets.join(", ") || "Add market context"}</strong></div><div><small>Open material briefs</small><strong>{state.data.briefs.length}</strong></div></section><section className="panel priority-panel"><p className="eyebrow">Strategic priorities</p><div className="semantic-chips">{state.data.profile?.strategic_priorities.map((item) => <span key={item}>{item}</span>)}{!state.data.profile?.strategic_priorities.length && <p>Add priorities to improve company-level ranking.</p>}</div></section><section className="company-decisions"><div className="section-heading"><h2>Company decisions requiring attention</h2><span>{state.data.briefs.length} open</span></div><div className="card-list">{state.data.briefs.length ? state.data.briefs.map((brief) => <BriefCard brief={brief} key={brief.id} />) : <section className="empty-brief"><h2>{stateMessages.companyBriefsEmpty.title}</h2><p>{stateMessages.companyBriefsEmpty.body}</p></section>}</div></section></>}
  </section></WorkspaceShell>;
}
