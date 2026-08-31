"use client";

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
};

export default function IntelligencePage() {
  const [state, setState] = useState<LoadState<Intelligence[]>>({ status: "loading" });
  const [domain, setDomain] = useState("ALL");
  const [priorityOnly, setPriorityOnly] = useState(false);

  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      setState({ status: "ready", data: await apiRequest<Intelligence[]>("/api/v1/signals") });
      void recordProductEvent("WIDER_INTELLIGENCE_VIEWED");
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Wider Intelligence could not be loaded."
      });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
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
            <p>Verified developments that do not currently require a Decision Brief.</p>
          </div>
          {state.status === "ready" && <div className="page-status"><i />Evidence current</div>}
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
                    <span>{item.primary_domain?.replaceAll("_", " ")}</span>
                    <span>{item.confidence_band} confidence</span>
                  </div>
                  <h2>{item.title || item.summary}</h2>
                  <p>{item.global_implication || item.summary}</p>
                  <footer>
                    <span><b>Source</b>{item.source_name}</span>
                    {item.source_url && <a href={item.source_url} rel="noreferrer" target="_blank">Open verified source →</a>}
                  </footer>
                </article>
              ))}
              {!visibleItems.length && (
                <section className="empty-brief">
                  <h2>{items.length ? "No intelligence matches these filters." : "No synthesized intelligence is available yet."}</h2>
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
