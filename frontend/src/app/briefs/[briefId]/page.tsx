"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CILPanel } from "@/components/cil-panel";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest, recordProductEvent } from "@/lib/api";
import { friendlyError } from "@/lib/product-copy/stateMessages";
import { Brief, LoadState } from "@/lib/types";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const actions = [
  ["ACKNOWLEDGED", "Acknowledge"],
  ["WATCHING", "Watch"],
  ["ESCALATED", "Escalate"],
  ["ACTED_ON", "Mark acted on"],
  ["DISMISSED", "Dismiss"],
] as const;
type BriefAction = (typeof actions)[number][0];

function readable(value?: string) {
  return value?.replaceAll("_", " ").toLowerCase() ?? "";
}

function date(value?: string) {
  return value ? new Date(value).toLocaleString() : "Not provided by the source";
}

export default function BriefDetailPage() {
  const id = String(useParams<{ briefId: string }>().briefId ?? "");
  const [state, setState] = useState<LoadState<Brief>>(
    UUID.test(id)
      ? { status: "loading" }
      : { status: "error", message: "This Decision Brief link is not valid." }
  );
  const [actionMessage, setActionMessage] = useState("");
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [showCil, setShowCil] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState<string>("");
  const [showEvidence, setShowEvidence] = useState(false);
  const [phase5Ui, setPhase5Ui] = useState(false);

  const load = useCallback(async () => {
    if (!UUID.test(id)) return;
    try {
      setState({ status: "loading" });
      const [data, capabilities] = await Promise.all([
        apiRequest<Brief>(`/api/v1/briefs/${id}`),
        apiRequest<{ phase5_new_ui_enabled: boolean }>("/api/v1/capabilities"),
      ]);
      setPhase5Ui(capabilities.phase5_new_ui_enabled);
      setState({ status: "ready", data });
      if (data.brief_contract?.entry_prompt) {
        setSelectedPrompt(data.brief_contract.entry_prompt);
      }
      if (capabilities.phase5_new_ui_enabled && data.response_options?.length) {
        void recordProductEvent("DECISION_PATHS_VIEWED", {
          object_type: "DECISION_BRIEF",
          object_id: id,
        });
      }
    } catch (error) {
      setState({
        status: "error",
        message: friendlyError(error, "We couldn't load this Decision Brief. Try again."),
      });
    }
  }, [id]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function act(actionType: BriefAction) {
    setActionMessage("");
    setPendingAction(actionType);
    try {
      await apiRequest(`/api/v1/briefs/${id}/actions`, {
        method: "POST",
        body: JSON.stringify({ action_type: actionType }),
      });
      setActionMessage(`${actions.find(([value]) => value === actionType)?.[1]} recorded.`);
      await load();
    } catch (error) {
      setActionMessage(friendlyError(error, "We couldn't record this action. Try again."));
    } finally {
      setPendingAction(null);
    }
  }

  function openEvidence() {
    setShowEvidence((value) => !value);
    if (!showEvidence) {
      void recordProductEvent("EVIDENCE_PANEL_OPENED", {
        object_type: "DECISION_BRIEF",
        object_id: id,
      });
    }
  }

  return (
    <WorkspaceShell>
      <section className="detail-page">
        <Link className="text-link detail-back" href="/briefing">
          ← Back to Briefing
        </Link>
        {state.status === "loading" && <ModuleLoading label="Loading Decision Brief" />}
        {state.status === "error" && (
          <ModuleFailure message={state.message} retry={() => void load()} />
        )}
        {state.status === "ready" && (
          <div className="decision-brief-grid">
            <article className="brief-detail brief-detail-v2">
              {/* Header meta */}
              <header>
                <div className="brief-meta">
                  <span className={`priority-chip priority-${state.data.relevance_band.toLowerCase()}`}>
                    {state.data.relevance_band}
                  </span>
                  <span>{readable(state.data.primary_domain)}</span>
                  {Number(state.data.material_change_count ?? 0) > 0 && (
                    <span className="updated-chip">Updated</span>
                  )}
                </div>
                <h1 style={{ margin: "0.5rem 0 0.25rem 0" }}>
                  {state.data.brief_contract?.decision ||
                    state.data.decision_prompt ||
                    state.data.what_changed}
                </h1>
                <p className="brief-deck">
                  {state.data.brief_contract?.why_now ||
                    state.data.why_it_matters ||
                    "Operational review required."}
                </p>
              </header>

              {/* 1. Decision Banner */}
              <section
                className="card highlight-card"
                style={{
                  marginTop: "1.5rem",
                  marginBottom: "1.5rem",
                  borderLeft: "4px solid var(--accent, #38bdf8)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <p className="eyebrow" style={{ margin: 0 }}>
                    Required Executive Decision
                  </p>
                  <span className="status-pill warning">DECISION REQUIRED</span>
                </div>
                <h2 style={{ fontSize: "1.25rem", margin: "0.5rem 0 0.25rem 0", lineHeight: 1.4 }}>
                  {state.data.brief_contract?.decision || state.data.decision_prompt || "Evaluate operational posture."}
                </h2>
                <p style={{ margin: 0, fontSize: "0.9rem", opacity: 0.85 }}>
                  Accountable Owner: <strong>{state.data.brief_contract?.owner || state.data.owner_roles?.join(", ") || "Leadership"}</strong> · {state.data.brief_contract?.timing || state.data.decision_window || "Immediate cycle"}
                </p>
              </section>

              {/* 2. Why Now */}
              <section>
                <p className="section-kicker">01</p>
                <h2>Why Now</h2>
                <p>
                  {state.data.brief_contract?.why_now ||
                    (Number(state.data.material_change_count ?? 0) > 0
                      ? "Recent material updates detected across verified sources."
                      : "Verified operational development requires timely determination.")}
                </p>
              </section>

              {/* 3. What Changed */}
              <section>
                <p className="section-kicker">02</p>
                <h2>What Changed</h2>
                <p>{state.data.brief_contract?.what_changed || state.data.what_changed}</p>
              </section>

              {/* 4. Exposure & 5. Stakes */}
              <section className="split-evidence">
                <div>
                  <p className="section-kicker">03</p>
                  <h2>Your Exposure</h2>
                  <p>{state.data.brief_contract?.exposure || state.data.exposure_summary || "Exposure is being assessed."}</p>
                  <div className="brief-chip-row">
                    {(state.data.brief_contract?.exposure_types || state.data.exposure_types || []).map((item) => (
                      <span key={item}>{readable(item)}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="section-kicker">04</p>
                  <h2>What Is at Stake</h2>
                  <p>{state.data.brief_contract?.stakes || state.data.stakes_summary || "Financial and operational stakes assessed."}</p>
                  <div className="brief-chip-row">
                    {(state.data.brief_contract?.stakes_types || state.data.stakes_types || []).map((item) => (
                      <span className="stakes-chip" key={item}>
                        {readable(item)}
                      </span>
                    ))}
                  </div>
                </div>
              </section>

              {/* 6. Decision Paths */}
              <section>
                <div className="section-heading">
                  <div>
                    <p className="section-kicker">05</p>
                    <h2>Decision Paths</h2>
                  </div>
                  {state.data.guidance_status && <span>{readable(state.data.guidance_status)}</span>}
                </div>
                {(state.data.brief_contract?.decision_paths?.length ||
                  state.data.response_options?.length) ? (
                  <div className="decision-paths">
                    {(state.data.brief_contract?.decision_paths || state.data.response_options || []).map((option) => (
                      <article key={option.option_code}>
                        <small>{option.option_code}</small>
                        <h3>{option.title}</h3>
                        <p>{option.description}</p>
                        {option.tradeoffs?.map((tradeoff) => (
                          <span key={tradeoff}>{tradeoff}</span>
                        ))}
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="quiet-state">
                    Stem needs more verified Company Context before presenting bounded response options.
                  </p>
                )}
              </section>

              {/* 7. Trade-offs */}
              <section>
                <p className="section-kicker">06</p>
                <h2>Trade-offs</h2>
                {state.data.brief_contract?.trade_offs?.length ? (
                  <ul>
                    {state.data.brief_contract.trade_offs.map((tradeoff, idx) => (
                      <li key={idx}>{tradeoff}</li>
                    ))}
                  </ul>
                ) : (
                  <p>Evaluate trade-offs between immediate mitigation costs and ongoing delay exposure.</p>
                )}
              </section>

              {/* 8. Validate Next */}
              <section>
                <p className="section-kicker">07</p>
                <h2>What to Validate Next</h2>
                {(state.data.brief_contract?.validate_next?.length ||
                  state.data.next_validation_steps?.length) ? (
                  <ol className="validation-steps">
                    {(state.data.brief_contract?.validate_next || state.data.next_validation_steps || []).map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ol>
                ) : (
                  <p>Confirm the current operational state with authorized counterparty logs.</p>
                )}
              </section>

              {/* 9. Unknowns */}
              <section>
                <p className="section-kicker">08</p>
                <h2>What Remains Unknown</h2>
                {(state.data.brief_contract?.unknowns?.length ||
                  state.data.uncertainties?.length) ? (
                  <ul>
                    {(state.data.brief_contract?.unknowns || state.data.uncertainties || []).map((item, idx) => (
                      <li key={idx}>{readable(item)}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No additional critical unknowns recorded.</p>
                )}
              </section>

              {/* 10. Owner / Timing */}
              <section>
                <p className="section-kicker">09</p>
                <h2>Accountability &amp; Timing</h2>
                <dl>
                  <dt>Decision Owner</dt>
                  <dd>{state.data.brief_contract?.owner || state.data.owner_roles?.join(", ") || "Executive Leadership"}</dd>
                  <dt>Target Window</dt>
                  <dd>{state.data.brief_contract?.timing || state.data.decision_window || "Immediate operational cycle"}</dd>
                </dl>
              </section>

              {/* 11. Evidence */}
              <section>
                <button
                  aria-expanded={showEvidence}
                  className="evidence-toggle"
                  onClick={openEvidence}
                  type="button"
                >
                  <span>
                    <span className="section-kicker">10</span>
                    <strong>Corroborated Evidence</strong>
                    <small>
                      {state.data.brief_contract?.evidence?.length ?? state.data.evidence?.length ?? 0} verified item
                      {(state.data.brief_contract?.evidence?.length ?? state.data.evidence?.length ?? 0) === 1 ? "" : "s"}
                    </small>
                  </span>
                  <b>{showEvidence ? "Hide" : "Review"}</b>
                </button>
                {showEvidence && (
                  <ul className="evidence-list">
                    {(state.data.brief_contract?.evidence || state.data.evidence || []).map((item) => (
                      <li key={item.id || item.source_name}>
                        <div>
                          <strong>
                            {item.title || item.source_name}
                            {item.is_primary ? " (Official source)" : ""}
                          </strong>
                          <small>
                            {item.source_name}
                            {"tier" in item && item.tier ? ` · Tier ${item.tier}` : ""}
                            {"published_at" in item && item.published_at ? ` · ${date(item.published_at)}` : ""}
                          </small>
                        </div>
                        {item.source_url && (
                          <a href={item.source_url} rel="noreferrer" target="_blank">
                            Open source
                          </a>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              {/* 12. Investigate with Cogent Action Card */}
              {state.data.brief_contract?.suggested_inquiries && (
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
                    <h3 style={{ margin: 0, fontSize: "1.1rem" }}>Investigate Decision with Cogent</h3>
                  </div>
                  <p style={{ margin: "0 0 1rem 0", fontSize: "0.95rem", opacity: 0.9 }}>
                    Deep-dive into trade-offs, validation prerequisites, and financial impact with Cogent. Click an angle to begin:
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                    {state.data.brief_contract.suggested_inquiries.map((inquiry, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => {
                          setSelectedPrompt(inquiry);
                          setShowCil(true);
                        }}
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

              {/* Timeline */}
              {state.data.timeline?.length ? (
                <section>
                  <p className="section-kicker">11</p>
                  <h2>Timeline</h2>
                  <ol className="brief-timeline">
                    {state.data.timeline.map((event, index) => (
                      <li key={`${event.event_type}-${index}`}>
                        <span />
                        <div>
                          <strong>{readable(event.event_type)}</strong>
                          <time dateTime={event.created_at}>
                            {new Date(event.created_at).toLocaleString()}
                          </time>
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              ) : null}
            </article>

            {/* Decision Rail */}
            <aside className="brief-context-rail">
              <section>
                <p className="eyebrow">Decision rail</p>
                <dl>
                  <div>
                    <dt>Materiality</dt>
                    <dd>{readable(state.data.relevance_band)} company relevance</dd>
                  </div>
                  <div>
                    <dt>Status</dt>
                    <dd>{readable(state.data.brief_status)}</dd>
                  </div>
                  <div>
                    <dt>Owner</dt>
                    <dd>{state.data.brief_contract?.owner || state.data.owner_roles?.join(", ") || "Leadership"}</dd>
                  </div>
                  <div>
                    <dt>Confidence</dt>
                    <dd>{readable(state.data.confidence_band) || "Reviewed"}</dd>
                  </div>
                  <div>
                    <dt>Decision window</dt>
                    <dd>{state.data.brief_contract?.timing || state.data.decision_window || "Monitor"}</dd>
                  </div>
                  <div>
                    <dt>Context matches</dt>
                    <dd>
                      {state.data.matched_company_objects?.join(", ") ||
                        "No named context matches are available."}
                    </dd>
                  </div>
                  <div>
                    <dt>Why shown</dt>
                    <dd>
                      {state.data.personal_priority_score
                        ? `${Math.round(Number(state.data.personal_priority_score) * 100)}% Decision Lens match`
                        : "Company priority"}
                    </dd>
                  </div>
                </dl>
              </section>

              <button
                className="primary-button investigate-button"
                onClick={() => {
                  setShowCil((val) => !val);
                  void recordProductEvent("CIL_OPENED", {
                    object_type: "DECISION_BRIEF",
                    object_id: id,
                  });
                }}
                type="button"
              >
                {showCil ? "Close Cogent Investigation" : "Investigate with Cogent"}
              </button>

              <div className="rail-actions">
                <h2>Actions</h2>
                {actions.map(([value, label]) => (
                  <button
                    disabled={pendingAction !== null}
                    key={value}
                    onClick={() => void act(value)}
                    type="button"
                  >
                    {pendingAction === value ? "Saving..." : label}
                  </button>
                ))}
              </div>
              {actionMessage && (
                <p aria-live="polite" className="form-message">
                  {actionMessage}
                </p>
              )}
              {showCil && (
                <CILPanel
                  anchorId={id}
                  anchorType="DECISION_BRIEF"
                  initialPrompt={selectedPrompt}
                  suggestedInquiries={state.data.brief_contract?.suggested_inquiries}
                />
              )}
            </aside>
          </div>
        )}
      </section>
    </WorkspaceShell>
  );
}
