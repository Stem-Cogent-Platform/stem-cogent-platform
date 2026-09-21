"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CILPanel } from "@/components/cil-panel";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type Evidence = {
  freshness?: string;
  effective_at?: string;
  id: string;
  title?: string;
  source_name: string;
  source_url?: string;
  canonical_url?: string;
  published_at?: string;
  detected_at?: string;
  is_primary?: boolean;
  duplicate_count?: number;
  tier?: number;
};

type SourceMetrics = {
  source_count: number;
  independent_source_count: number;
  primary_source_count: number;
  corroboration_strength: string;
};

type DossierSourceItem = {
  id?: string;
  source_name: string;
  source_url?: string;
  canonical_url?: string;
  published_at?: string;
  detected_at?: string;
  source_type?: string;
  tier?: number;
  is_primary?: boolean;
};

type RelatedIntelligenceItem = {
  id: string;
  title: string;
  published_at?: string;
  source_name?: string;
  source_url?: string;
  relationship?: string;
};

type HistoricalContextItem = {
  id: string;
  title: string;
  published_at?: string;
  context_note?: string;
};

type DossierContract = {
  judgment: string;
  what_changed: string;
  why_it_matters: string;
  exposure: string[];
  implications: string[];
  decision_posture: "NO_ACTION" | "MONITOR" | "INVESTIGATE" | "DECISION_REQUIRED";
  what_we_know: string[];
  what_we_do_not_know: string[];
  related_intelligence: RelatedIntelligenceItem[];
  historical_context: HistoricalContextItem[];
  sources: DossierSourceItem[];
  source_metrics: {
    source_count?: number;
    independent_source_count?: number;
    primary_source_count?: number;
    corroboration_strength?: string;
  };
  investigate_with_cogent: {
    signal_id: string;
    entry_prompt: string;
    suggested_inquiries: string[];
  };
};

type Dossier = {
  dossier?: DossierContract;
  signal: Evidence & {
    evidence_excerpt?: string;
    primary_domain?: string;
    confidence_band?: string;
    urgency_band?: string;
    summary?: string;
    global_implication?: string;
    confidence_note?: string;
    key_developments?: string[];
    llm_synthesis_failed?: boolean;
    synthesized_at?: string;
    subcategory_tags?: string[];
  };
  entities: { id: string; canonical_name: string; entity_type: string }[];
  evidence: Evidence[];
  source_metrics?: SourceMetrics;
  related_intelligence?: Evidence[];
  historical_context?: Evidence[];
  tenant_interpretation?: {
    relevance_band: string;
    decision_required: boolean;
    matched_company_objects: string[];
  } | null;
};

function date(value?: string) {
  return value ? new Date(value).toLocaleString() : "Not provided by the source";
}

function postureColor(posture?: string) {
  switch (posture) {
    case "DECISION_REQUIRED":
      return "status-pill error";
    case "INVESTIGATE":
      return "status-pill warning";
    case "MONITOR":
      return "status-pill info";
    default:
      return "status-pill neutral";
  }
}

export default function SignalPage() {
  const id = String(useParams<{ signalId: string }>().signalId ?? "");
  const [state, setState] = useState<LoadState<Dossier>>({ status: "loading" });
  const [selectedPrompt, setSelectedPrompt] = useState<string>("");

  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      const data = await apiRequest<Dossier>(`/api/v1/signals/${id}`);
      setState({ status: "ready", data });
      if (data.dossier?.investigate_with_cogent.entry_prompt) {
        setSelectedPrompt(data.dossier.investigate_with_cogent.entry_prompt);
      }
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "This signal is unavailable.",
      });
    }
  }, [id]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  return (
    <WorkspaceShell>
      <section className="content-page">
        <Link href="/intelligence">← Intelligence</Link>
        {state.status === "loading" && <ModuleLoading label="Loading signal dossier" />}
        {state.status === "error" && (
          <ModuleFailure message={state.message} retry={() => void load()} />
        )}
        {state.status === "ready" && (
          <>
            <div className="page-heading">
              <div>
                <p className="eyebrow">Signal Dossier</p>
                <h1>{state.data.signal?.title || "Source development"}</h1>
                <p>{state.data.signal?.primary_domain?.replaceAll("_", " ")}</p>
              </div>
            </div>

            <div className="detail-grid">
              <article className="brief-detail">
                {/* 1. Judgment & Decision Posture */}
                <section className="card highlight-card" style={{ marginBottom: "1.5rem" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "1rem",
                      marginBottom: "0.75rem",
                    }}
                  >
                    <p className="eyebrow" style={{ margin: 0 }}>
                      Intelligence Judgment
                    </p>
                    <span
                      className={postureColor(
                        state.data.dossier?.decision_posture ??
                          (state.data.tenant_interpretation?.decision_required
                            ? "DECISION_REQUIRED"
                            : "MONITOR")
                      )}
                    >
                      {state.data.dossier?.decision_posture?.replaceAll("_", " ") ??
                        (state.data.tenant_interpretation?.decision_required
                          ? "DECISION REQUIRED"
                          : "MONITOR")}
                    </span>
                  </div>
                  <h2 style={{ fontSize: "1.25rem", lineHeight: "1.4", margin: 0 }}>
                    {state.data.dossier?.judgment ||
                      state.data.signal?.summary ||
                      "Operational assessment in progress."}
                  </h2>
                </section>

                {/* 2. What Changed */}
                <p className="eyebrow">
                  {state.data.signal?.freshness === "HISTORICAL"
                    ? "Historical Context"
                    : state.data.signal?.freshness === "DATE_UNCERTAIN"
                    ? "Publication Date Unconfirmed"
                    : state.data.signal?.freshness?.toLowerCase()}
                </p>
                <h2>1. What Changed</h2>
                <p>
                  {state.data.dossier?.what_changed ||
                    state.data.signal?.summary ||
                    "A synthesized summary is not yet available. Review the source evidence below."}
                </p>
                {!state.data.signal?.llm_synthesis_failed &&
                state.data.signal?.key_developments?.length ? (
                  <ul>
                    {state.data.signal.key_developments.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                ) : null}

                {/* 3. Why It Matters to You */}
                <h2>2. Why It Matters to You</h2>
                <div
                  style={{
                    padding: "1rem",
                    borderRadius: "8px",
                    background: "var(--surface-subtle, rgba(255,255,255,0.03))",
                    marginBottom: "1.5rem",
                  }}
                >
                  <p style={{ margin: 0 }}>
                    {state.data.dossier?.why_it_matters ||
                      (state.data.tenant_interpretation ? (
                        <>
                          Company interpretation:{" "}
                          {state.data.tenant_interpretation.relevance_band.toLowerCase()}{" "}
                          relevance.{" "}
                          {state.data.tenant_interpretation.matched_company_objects.length
                            ? `Matches your configured ${state.data.tenant_interpretation.matched_company_objects.join(
                                ", "
                              )}.`
                            : "Matches configured decision criteria."}
                        </>
                      ) : (
                        "No current company relevance assessment is available for this development."
                      ))}
                  </p>
                </div>

                {/* 4. Exposure & 5. Implications */}
                <h2>3. Exposure &amp; Implications</h2>
                {state.data.dossier?.exposure && state.data.dossier.exposure.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
                    {state.data.dossier.exposure.map((exp, idx) => (
                      <span
                        key={idx}
                        style={{
                          fontSize: "0.75rem",
                          padding: "0.25rem 0.6rem",
                          borderRadius: "4px",
                          background: "var(--accent-subtle, rgba(56, 189, 248, 0.15))",
                          color: "var(--accent, #38bdf8)",
                          fontWeight: 500,
                        }}
                      >
                        {exp}
                      </span>
                    ))}
                  </div>
                )}
                {state.data.dossier?.implications?.length ? (
                  <ul>
                    {state.data.dossier.implications.map((imp, idx) => (
                      <li key={idx}>{imp}</li>
                    ))}
                  </ul>
                ) : state.data.signal?.global_implication ? (
                  <p>{state.data.signal.global_implication}</p>
                ) : null}

                {/* 6. Decision Posture */}
                <h2>4. Decision Posture</h2>
                <p>
                  Recommended Stance:{" "}
                  <strong>
                    {state.data.dossier?.decision_posture?.replaceAll("_", " ") ??
                      (state.data.tenant_interpretation?.decision_required
                        ? "DECISION REQUIRED"
                        : "MONITOR")}
                  </strong>
                </p>

                {/* 7. What We Know vs. 8. What We Do Not Know */}
                <h2>5. Intelligence Grounding: Facts vs. Unknowns</h2>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                    gap: "1rem",
                    marginBottom: "1.5rem",
                  }}
                >
                  <div
                    style={{
                      padding: "1rem",
                      borderRadius: "8px",
                      background: "rgba(16, 185, 129, 0.05)",
                      borderLeft: "3px solid #10b981",
                    }}
                  >
                    <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "0.95rem", color: "#10b981" }}>
                      What We Know (Verified Facts)
                    </h3>
                    {state.data.dossier?.what_we_know?.length ? (
                      <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
                        {state.data.dossier.what_we_know.map((item, idx) => (
                          <li key={idx} style={{ fontSize: "0.9rem" }}>
                            {item}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p style={{ margin: 0, fontSize: "0.9rem" }}>
                        {state.data.signal?.summary || "Initial reports under observation."}
                      </p>
                    )}
                  </div>

                  <div
                    style={{
                      padding: "1rem",
                      borderRadius: "8px",
                      background: "rgba(245, 158, 11, 0.05)",
                      borderLeft: "3px solid #f59e0b",
                    }}
                  >
                    <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "0.95rem", color: "#f59e0b" }}>
                      What We Do Not Know (Gaps &amp; Uncertainties)
                    </h3>
                    {state.data.dossier?.what_we_do_not_know?.length ? (
                      <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
                        {state.data.dossier.what_we_do_not_know.map((item, idx) => (
                          <li key={idx} style={{ fontSize: "0.9rem" }}>
                            {item}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p style={{ margin: 0, fontSize: "0.9rem" }}>
                        {state.data.signal?.confidence_note ||
                          "Implementation guidance and formal circular status unconfirmed."}
                      </p>
                    )}
                  </div>
                </div>

                {/* 9. Related Intelligence & 10. Historical Context */}
                <h2>6. Context &amp; Correlated Intelligence</h2>
                {state.data.dossier?.related_intelligence?.length ||
                state.data.related_intelligence?.length ? (
                  <div>
                    <p className="eyebrow" style={{ marginTop: "0.5rem" }}>
                      Related Developments
                    </p>
                    <ul>
                      {(state.data.dossier?.related_intelligence ||
                        state.data.related_intelligence?.filter(
                          (item) => item.freshness !== "HISTORICAL"
                        ) ||
                        []
                      ).map((item) => (
                        <li key={item.id}>
                          <Link href={`/signals/${item.id}`}>{item.title}</Link>
                          {item.published_at && (
                            <small style={{ marginLeft: "0.5rem", opacity: 0.7 }}>
                              · {date(item.published_at)}
                            </small>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p>No additional related developments are stored.</p>
                )}

                <p className="eyebrow" style={{ marginTop: "1rem" }}>
                  Historical Precedents
                </p>
                {state.data.dossier?.historical_context?.length ||
                state.data.historical_context?.length ? (
                  <ul>
                    {(state.data.dossier?.historical_context ||
                      state.data.historical_context ||
                      []
                    ).map((item) => (
                      <li key={item.id}>
                        <Link href={`/signals/${item.id}`}>{item.title}</Link>
                        <p style={{ margin: "0.2rem 0", fontSize: "0.85rem", opacity: 0.8 }}>
                          Originally published: {date(item.published_at)}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>No related historical evidence is stored for this development.</p>
                )}

                {/* 11. Sources (Citation-First Evidence) */}
                <h2>7. Corroborated Sources &amp; Evidence</h2>
                <dl>
                  <dt>Published</dt>
                  <dd>{date(state.data.signal?.published_at)}</dd>
                  <dt>Independent Sources</dt>
                  <dd>
                    {state.data.dossier?.source_metrics?.independent_source_count ??
                      state.data.source_metrics?.independent_source_count ??
                      state.data.evidence?.length ??
                      1}
                  </dd>
                  <dt>Corroboration</dt>
                  <dd>
                    {(
                      state.data.dossier?.source_metrics?.corroboration_strength ??
                      state.data.source_metrics?.corroboration_strength ??
                      "UNVERIFIED"
                    )
                      .replaceAll("_", " ")
                      .toLowerCase()}
                  </dd>
                </dl>

                <ul className="evidence-list">
                  {(state.data.dossier?.sources || state.data.evidence || []).map((item, idx) => {
                    const key = item.id || `ev-${idx}`;
                    const isPrimary = "is_primary" in item && item.is_primary;
                    const url = item.source_url || ("canonical_url" in item ? item.canonical_url : undefined);
                    return (
                      <li key={key}>
                        <div>
                          <strong>
                            {item.source_name}
                            {isPrimary ? " (Official source)" : ""}
                          </strong>
                          <small>
                            {"tier" in item && item.tier ? `Tier ${item.tier} · ` : ""}
                            Published: {date(item.published_at)}
                          </small>
                        </div>
                        {url && (
                          <a href={url} target="_blank" rel="noreferrer">
                            Open source
                          </a>
                        )}
                      </li>
                    );
                  })}
                </ul>

                {/* 12. Investigate with Cogent Banner */}
                {state.data.dossier?.investigate_with_cogent && (
                  <section
                    className="card"
                    style={{
                      marginTop: "2rem",
                      background: "linear-gradient(135deg, rgba(56, 189, 248, 0.08), rgba(99, 102, 241, 0.08))",
                      border: "1px solid rgba(56, 189, 248, 0.2)",
                      borderRadius: "8px",
                      padding: "1.25rem",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
                      <span style={{ fontSize: "1.2rem" }}>🔍</span>
                      <h3 style={{ margin: 0, fontSize: "1.1rem" }}>Investigate with Cogent</h3>
                    </div>
                    <p style={{ margin: "0 0 1rem 0", fontSize: "0.95rem", opacity: 0.9 }}>
                      Investigate this development with Cogent as your bounded intelligence analyst. Click an inquiry angle to start immediately:
                    </p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                      {state.data.dossier.investigate_with_cogent.suggested_inquiries.map((inquiry, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => setSelectedPrompt(inquiry)}
                          className="button-secondary"
                          style={{
                            fontSize: "0.85rem",
                            padding: "0.4rem 0.8rem",
                            cursor: "pointer",
                            background: "var(--surface, #1e293b)",
                            border: "1px solid rgba(255,255,255,0.15)",
                            borderRadius: "6px",
                            textAlign: "left",
                          }}
                        >
                          {inquiry}
                        </button>
                      ))}
                    </div>
                  </section>
                )}
              </article>

              <CILPanel
                anchorId={id}
                anchorType="SIGNAL"
                initialPrompt={selectedPrompt}
                suggestedInquiries={state.data.dossier?.investigate_with_cogent.suggested_inquiries}
              />
            </div>
          </>
        )}
      </section>
    </WorkspaceShell>
  );
}
