"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { BriefCard } from "@/components/brief-card";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { stateMessages } from "@/lib/product-copy/stateMessages";
import { Brief, LoadState } from "@/lib/types";

type CompanyObject = {
  id: string;
  name: string;
  object_type: string;
  active: boolean;
  entity_id?: string;
};

type FocusItem = {
  id: string;
  label: string;
  focus_type: string;
  weight?: number;
  entity_id?: string;
};

type CompanyData = {
  profile: null | {
    business_categories: string[];
    strategic_priorities: string[];
    operating_markets: string[];
  };
  objects: CompanyObject[];
  focus: FocusItem[];
  context_status: {
    complete: boolean;
    completeness: number;
    missing_fields?: string[];
    version: number;
  };
  briefs: Brief[];
};

export default function CompanyPage() {
  const [state, setState] = useState<LoadState<CompanyData>>({ status: "loading" });

  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      const [briefsData, focusData] = await Promise.all([
        apiRequest<{
          profile: CompanyData["profile"];
          objects?: CompanyObject[];
          context_status: CompanyData["context_status"];
          briefs: Brief[];
        }>("/api/v1/company/briefs"),
        apiRequest<FocusItem[]>("/api/v1/me/focus-areas").catch(() => [] as FocusItem[]),
      ]);

      setState({
        status: "ready",
        data: {
          profile: briefsData.profile,
          objects: briefsData.objects || [],
          focus: focusData,
          context_status: briefsData.context_status,
          briefs: briefsData.briefs,
        },
      });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Company Lens could not be loaded.",
      });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  return (
    <WorkspaceShell>
      <section className="content-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Organizational Model & Scope</p>
            <h1>Company</h1>
            <p style={{ marginTop: "4px", fontSize: "0.88rem", color: "var(--text-secondary)", maxWidth: "760px" }}>
              Your shared organizational model, strategic priorities, and active monitoring scope. Stem continuously tracks these counterparties and market dependencies on behalf of your leadership team.
            </p>
          </div>
          <Link className="secondary-button" href="/briefing">
            View My Briefing
          </Link>
        </div>

        {state.status === "loading" && <ModuleLoading label="Loading Company Context and Decisions..." />}
        {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}

        {state.status === "ready" && (
          <>
            {/* Top Metrics Summary */}
            <section className="company-summary">
              <div>
                <small>Company context</small>
                <strong>
                  {state.data.context_status.complete
                    ? `${state.data.profile?.business_categories?.join(", ") || "Configured"} · v${state.data.context_status.version}`
                    : `${Math.round((state.data.context_status.completeness || 0) * 100)}% complete`}
                </strong>
              </div>
              <div>
                <small>Operating markets</small>
                <strong>{state.data.profile?.operating_markets?.join(", ") || "Nigeria"}</strong>
              </div>
              <div>
                <small>Open material briefs</small>
                <strong>{state.data.briefs.length}</strong>
              </div>
            </section>

            {/* Strategic Priorities */}
            <section className="panel priority-panel" style={{ marginBottom: "24px" }}>
              <p className="eyebrow">Strategic priorities</p>
              <div className="semantic-chips" style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "8px" }}>
                {state.data.profile?.strategic_priorities?.map((item) => (
                  <span
                    key={item}
                    style={{
                      background: "var(--accent-soft)",
                      color: "var(--accent)",
                      borderRadius: "8px",
                      padding: "6px 12px",
                      fontSize: "0.82rem",
                      fontWeight: 600,
                    }}
                  >
                    {item}
                  </span>
                ))}
                {!state.data.profile?.strategic_priorities?.length && (
                  <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", margin: 0 }}>
                    Add strategic priorities in settings to guide company-level ranking.
                  </p>
                )}
              </div>
            </section>

            {/* Monitoring Scope Section: Replaces standalone Watchlist */}
            <section
              className="panel monitoring-scope-panel"
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border)",
                borderRadius: "16px",
                padding: "24px",
                marginBottom: "28px",
              }}
            >
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
                <div>
                  <p className="eyebrow" style={{ margin: 0, color: "var(--accent)" }}>Automated Scope</p>
                  <h2 style={{ fontSize: "1.25rem", margin: "4px 0 8px" }}>
                    Monitoring Scope: Company Context + Focus Areas
                  </h2>
                  <p style={{ color: "var(--text-secondary)", fontSize: "0.88rem", lineHeight: 1.5, margin: 0, maxWidth: "720px" }}>
                    Stem continuously tracks external market changes matching your configured company dependencies, competitors,
                    products, and personal focus areas. You do not need to maintain a separate manual watchlist.
                  </p>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <Link href="/settings" className="secondary-button" style={{ fontSize: "0.8rem", padding: "6px 14px" }}>
                    Adjust Context in Settings
                  </Link>
                </div>
              </div>

              {/* Categorized Scope Grid */}
              <div style={{ display: "grid", gap: "16px", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", marginTop: "16px" }}>
                {/* Competitors */}
                <div style={{ background: "var(--bg-subtle)", borderRadius: "12px", padding: "16px", border: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                    <strong style={{ fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)" }}>
                      Competitors
                    </strong>
                    <span style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600 }}>
                      {state.data.objects.filter((o) => o.object_type === "COMPETITOR").length} tracked
                    </span>
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {state.data.objects.filter((o) => o.object_type === "COMPETITOR").map((obj) => (
                      obj.entity_id ? (
                        <Link
                          key={obj.id}
                          href={`/entities/${obj.entity_id}`}
                          style={{
                            background: "var(--bg-surface)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            padding: "4px 8px",
                            fontSize: "0.8rem",
                            color: "var(--text-primary)",
                            textDecoration: "none",
                          }}
                        >
                          {obj.name} ↗
                        </Link>
                      ) : (
                        <span
                          key={obj.id}
                          style={{
                            background: "var(--bg-surface)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            padding: "4px 8px",
                            fontSize: "0.8rem",
                            color: "var(--text-primary)",
                          }}
                        >
                          {obj.name}
                        </span>
                      )
                    ))}
                    {!state.data.objects.some((o) => o.object_type === "COMPETITOR") && (
                      <small style={{ color: "var(--text-secondary)" }}>No competitors configured</small>
                    )}
                  </div>
                </div>

                {/* Dependencies / Rails */}
                <div style={{ background: "var(--bg-subtle)", borderRadius: "12px", padding: "16px", border: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                    <strong style={{ fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)" }}>
                      Dependencies & Rails
                    </strong>
                    <span style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600 }}>
                      {state.data.objects.filter((o) => o.object_type === "DEPENDENCY").length} tracked
                    </span>
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {state.data.objects.filter((o) => o.object_type === "DEPENDENCY").map((obj) => (
                      obj.entity_id ? (
                        <Link
                          key={obj.id}
                          href={`/entities/${obj.entity_id}`}
                          style={{
                            background: "var(--bg-surface)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            padding: "4px 8px",
                            fontSize: "0.8rem",
                            color: "var(--text-primary)",
                            textDecoration: "none",
                          }}
                        >
                          {obj.name} ↗
                        </Link>
                      ) : (
                        <span
                          key={obj.id}
                          style={{
                            background: "var(--bg-surface)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            padding: "4px 8px",
                            fontSize: "0.8rem",
                            color: "var(--text-primary)",
                          }}
                        >
                          {obj.name}
                        </span>
                      )
                    ))}
                    {!state.data.objects.some((o) => o.object_type === "DEPENDENCY") && (
                      <small style={{ color: "var(--text-secondary)" }}>No dependencies configured</small>
                    )}
                  </div>
                </div>

                {/* Regulators & Authorities */}
                <div style={{ background: "var(--bg-subtle)", borderRadius: "12px", padding: "16px", border: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                    <strong style={{ fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)" }}>
                      Regulators & Authorities
                    </strong>
                    <span style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600 }}>
                      {state.data.objects.filter((o) => o.object_type === "REGULATOR").length} tracked
                    </span>
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {state.data.objects.filter((o) => o.object_type === "REGULATOR").map((obj) => (
                      obj.entity_id ? (
                        <Link
                          key={obj.id}
                          href={`/entities/${obj.entity_id}`}
                          style={{
                            background: "var(--bg-surface)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            padding: "4px 8px",
                            fontSize: "0.8rem",
                            color: "var(--text-primary)",
                            textDecoration: "none",
                          }}
                        >
                          {obj.name} ↗
                        </Link>
                      ) : (
                        <span
                          key={obj.id}
                          style={{
                            background: "var(--bg-surface)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            padding: "4px 8px",
                            fontSize: "0.8rem",
                            color: "var(--text-primary)",
                          }}
                        >
                          {obj.name}
                        </span>
                      )
                    ))}
                    {!state.data.objects.some((o) => o.object_type === "REGULATOR") && (
                      <small style={{ color: "var(--text-secondary)" }}>No regulatory bodies configured</small>
                    )}
                  </div>
                </div>

                {/* Partners & Counterparties */}
                <div style={{ background: "var(--bg-subtle)", borderRadius: "12px", padding: "16px", border: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                    <strong style={{ fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)" }}>
                      Partners & Counterparties
                    </strong>
                    <span style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600 }}>
                      {state.data.objects.filter((o) => o.object_type === "PARTNER").length} tracked
                    </span>
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {state.data.objects.filter((o) => o.object_type === "PARTNER").map((obj) => (
                      obj.entity_id ? (
                        <Link
                          key={obj.id}
                          href={`/entities/${obj.entity_id}`}
                          style={{
                            background: "var(--bg-surface)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            padding: "4px 8px",
                            fontSize: "0.8rem",
                            color: "var(--text-primary)",
                            textDecoration: "none",
                          }}
                        >
                          {obj.name} ↗
                        </Link>
                      ) : (
                        <span
                          key={obj.id}
                          style={{
                            background: "var(--bg-surface)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            padding: "4px 8px",
                            fontSize: "0.8rem",
                            color: "var(--text-primary)",
                          }}
                        >
                          {obj.name}
                        </span>
                      )
                    ))}
                    {!state.data.objects.some((o) => o.object_type === "PARTNER") && (
                      <small style={{ color: "var(--text-secondary)" }}>No partners configured</small>
                    )}
                  </div>
                </div>

                {/* Products & Lines */}
                <div style={{ background: "var(--bg-subtle)", borderRadius: "12px", padding: "16px", border: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                    <strong style={{ fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)" }}>
                      Products & Lines
                    </strong>
                    <span style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600 }}>
                      {state.data.objects.filter((o) => o.object_type === "PRODUCT").length} tracked
                    </span>
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {state.data.objects.filter((o) => o.object_type === "PRODUCT").map((obj) => (
                      <span
                        key={obj.id}
                        style={{
                          background: "var(--bg-surface)",
                          border: "1px solid var(--border)",
                          borderRadius: "6px",
                          padding: "4px 8px",
                          fontSize: "0.8rem",
                          color: "var(--text-primary)",
                        }}
                      >
                        {obj.name}
                      </span>
                    ))}
                    {!state.data.objects.some((o) => o.object_type === "PRODUCT") && (
                      <small style={{ color: "var(--text-secondary)" }}>No product lines configured</small>
                    )}
                  </div>
                </div>

                {/* Personal Focus Areas */}
                <div style={{ background: "var(--bg-subtle)", borderRadius: "12px", padding: "16px", border: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                    <strong style={{ fontSize: "0.82rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)" }}>
                      Personal Focus Areas
                    </strong>
                    <span style={{ fontSize: "0.75rem", color: "var(--accent)", fontWeight: 600 }}>
                      {state.data.focus.length} active
                    </span>
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {state.data.focus.map((f) => (
                      <span
                        key={f.id}
                        style={{
                          background: "var(--bg-surface)",
                          border: "1px solid var(--border)",
                          borderRadius: "6px",
                          padding: "4px 8px",
                          fontSize: "0.8rem",
                          color: "var(--text-primary)",
                        }}
                      >
                        🎯 {f.label}
                      </span>
                    ))}
                    {!state.data.focus.length && (
                      <small style={{ color: "var(--text-secondary)" }}>No focus areas set</small>
                    )}
                  </div>
                </div>
              </div>
            </section>

            {/* Company Decisions Section */}
            <section className="company-decisions">
              <div className="section-heading">
                <h2>Company decisions requiring attention</h2>
                <span>{state.data.briefs.length} open</span>
              </div>
              <div className="card-list">
                {state.data.briefs.length ? (
                  state.data.briefs.map((brief) => <BriefCard brief={brief} key={brief.id} />)
                ) : (
                  <section className="empty-brief">
                    <h2>{stateMessages.companyBriefsEmpty.title}</h2>
                    <p>{stateMessages.companyBriefsEmpty.body}</p>
                  </section>
                )}
              </div>
            </section>
          </>
        )}
      </section>
    </WorkspaceShell>
  );
}
