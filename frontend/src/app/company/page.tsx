"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { BriefCard } from "@/components/brief-card";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { Brief, LoadState } from "@/lib/types";

type Company = { profile: null | { strategic_priorities: string[]; operating_markets: string[] }; briefs: Brief[] };
export default function CompanyPage() {
  const [state, setState] = useState<LoadState<Company>>({ status: "loading" });
  const load = useCallback(async () => { try { setState({ status: "ready", data: await apiRequest<Company>("/api/v1/company") }); } catch (error) { setState({ status: "error", message: error instanceof Error ? error.message : "Company Lens could not be loaded." }); } }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  return <WorkspaceShell><section className="content-page"><div className="page-heading"><div><p className="eyebrow">Shared organisational view</p><h1>Company Lens</h1></div><Link className="secondary-button" href="/briefing">Switch to My Lens</Link></div>
    {state.status === "loading" && <ModuleLoading />}{state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
    {state.status === "ready" && <><section className="company-summary"><div><small>Markets</small><strong>{state.data.profile?.operating_markets.join(", ") || "Context incomplete"}</strong></div><div><small>Strategic priorities</small><strong>{state.data.profile?.strategic_priorities.join(", ") || "Not configured"}</strong></div><div><small>Open material briefs</small><strong>{state.data.briefs.length}</strong></div></section><div className="card-list">{state.data.briefs.length ? state.data.briefs.map((brief) => <BriefCard brief={brief} key={brief.id} />) : <section className="empty-brief"><h2>No company-level Decision Briefs are open.</h2><p>Stem will surface shared material developments when evidence and Company Context support them.</p></section>}</div></>}
  </section></WorkspaceShell>;
}
