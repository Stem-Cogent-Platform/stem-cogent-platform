"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest, recordProductEvent } from "@/lib/api";
import { LoadState } from "@/lib/types";

type Intelligence = {
  id: string;
  signal_id: string;
  title?: string;
  summary?: string;
  global_implication?: string;
  primary_domain?: string;
  urgency_band?: string;
  confidence_band?: string;
  source_name: string;
  source_url?: string;
  published_at?: string;
  detected_at?: string;
  llm_synthesis_failed?: boolean;
  freshness?: string;
};

export default function IntelligencePage() {
  const [state, setState] = useState<LoadState<Intelligence[]>>({ status: "loading" });
  const [domain, setDomain] = useState("ALL");
  const [freshness, setFreshness] = useState("CURRENT");
  const [search, setSearch] = useState("");
  const [priorityOnly, setPriorityOnly] = useState(false);

  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      setState({ status: "ready", data: await apiRequest<Intelligence[]>(`/api/v1/signals?freshness=${freshness}&q=${encodeURIComponent(search)}`) });
      void recordProductEvent("WIDER_INTELLIGENCE_VIEWED");
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Wider Intelligence could not be loaded."
      });
    }
  }, [freshness, search]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 250);
    return () => window.clearTimeout(timer);
  }, [load]);

  const items = state.status === "ready" ? state.data : [];
  const domains = Array.from(
    new Set(items.map((item) => item.primary_domain).filter((value): value is string => Boolean(value)))
  );
  const visibleItems = items.filter(
    (item) =>
      (domain === "ALL" || item.primary_domain === domain) &&
      (!priorityOnly || ["CRITICAL", "HIGH"].includes(item.urgency_band ?? ""))
  );

  return (
    <WorkspaceShell>
      <section className="content-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Supporting market view</p>
            <h1>Wider Intelligence</h1>
            <p>Source-backed market developments. Open a dossier to review the evidence and analysis status.</p>
          </div>
          {state.status === "ready" && <div className="page-status">{items.length} stored developments</div>}
        </div>
        <div className="intelligence-toolbar">
          <label>Time period <select aria-label="Intelligence time period" value={freshness} onChange={(event) => setFreshness(event.target.value)}>
            <option value="CURRENT">Current and recent</option><option value="HISTORICAL">Historical context</option>
            <option value="DATE_UNCERTAIN">Date unconfirmed</option><option value="ALL">All stored intelligence</option>
          </select></label>
          <label>Search intelligence <input value={search} onChange={(event) => setSearch(event.target.value)} maxLength={200} type="search" /></label>
        </div>
        {state.status === "loading" && <ModuleLoading label="Loading Wider Intelligence" />}
        {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
        {state.status === "ready" && (
          <>
            <div className="intelligence-toolbar">
              <div className="filter-pills">
                <button className={domain === "ALL" ? "active" : ""} onClick={() => setDomain("ALL")} type="button">
                  All domains <span>{items.length}</span>
                </button>
                {domains.map((itemDomain) => (
                  <button className={domain === itemDomain ? "active" : ""} key={itemDomain} onClick={() => setDomain(itemDomain)} type="button">
                    {itemDomain.replaceAll("_", " ")}
                  </button>
                ))}
              </div>
              <label className="priority-toggle">
                <input checked={priorityOnly} onChange={(event) => setPriorityOnly(event.target.checked)} type="checkbox" />
                <span>Priority only</span>
              </label>
            </div>
            <div className="intelligence-list">
              {visibleItems.map((item) => (
                <article key={item.id}>
                  <div className="signal-accent" />
                  <div className="brief-meta">
                    <span className={`priority-chip priority-${(item.urgency_band ?? "standard").toLowerCase()}`}>{item.urgency_band ?? "MONITOR"}</span>
                    <span>{item.primary_domain?.replaceAll("_", " ")}</span><span>{item.freshness === "HISTORICAL" ? "Historical context" : item.freshness === "DATE_UNCERTAIN" ? "Publication date unconfirmed" : item.freshness?.toLowerCase()}</span>
                    <span>{item.confidence_band?.replaceAll("_", " ").toLowerCase() || "Unassessed"} confidence</span>
                    {item.llm_synthesis_failed && <span>Analysis unavailable</span>}
                  </div>
                  <h2><Link href={`/signals/${item.signal_id}`} prefetch={false}>{item.title || item.summary}</Link></h2>
                  <p>{item.llm_synthesis_failed ? "Source evidence retained. Open the dossier to review what is known and what remains unassessed." : item.global_implication || item.summary}</p>
                  <p>{item.published_at ? `Published ${new Date(item.published_at).toLocaleDateString()}` : "Publication date unavailable"}{item.detected_at ? ` · Detected ${new Date(item.detected_at).toLocaleDateString()}` : ""}</p>
                  <footer>
                    <span><b>Source</b>{item.source_name}</span>
                    <Link href={`/signals/${item.signal_id}`} prefetch={false}>View dossier →</Link>
                    {item.source_url && <a href={item.source_url} rel="noreferrer" target="_blank">Open source ↗</a>}
                  </footer>
                </article>
              ))}
              {!visibleItems.length && (
                <section className="empty-brief">
                  <h2>{items.length ? "No intelligence matches these filters." : freshness === "CURRENT" ? "No verified recent intelligence matches these filters." : "No stored intelligence matches these filters."}</h2>
                  <p>
                    {items.length
                      ? "Choose another domain or include standard monitoring items."
                      : "Stem is preparing verified market developments. New intelligence will appear here when the evidence is ready."}
                  </p>
                </section>
              )}
            </div>
          </>
        )}
      </section>
    </WorkspaceShell>
  );
}
