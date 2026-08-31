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
const actions = [["ACKNOWLEDGED", "Acknowledge"], ["WATCHING", "Watch"], ["ESCALATED", "Escalate"], ["ACTED_ON", "Mark acted on"], ["DISMISSED", "Dismiss"]] as const;
type BriefAction = (typeof actions)[number][0];

function readable(value?: string) { return value?.replaceAll("_", " ").toLowerCase() ?? ""; }

export default function BriefDetailPage() {
  const id = String(useParams<{ briefId: string }>().briefId ?? "");
  const [state, setState] = useState<LoadState<Brief>>(UUID.test(id) ? { status: "loading" } : { status: "error", message: "This Decision Brief link is not valid." });
  const [actionMessage, setActionMessage] = useState("");
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [showCil, setShowCil] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);

  const load = useCallback(async () => {
    if (!UUID.test(id)) return;
    try {
      setState({ status: "loading" });
      const data = await apiRequest<Brief>(`/api/v1/briefs/${id}`);
      setState({ status: "ready", data });
      if (data.response_options?.length) void recordProductEvent("DECISION_PATHS_VIEWED", { object_type: "DECISION_BRIEF", object_id: id });
    } catch (error) {
      setState({ status: "error", message: friendlyError(error, "We couldn't load this Decision Brief. Try again.") });
    }
  }, [id]);

  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);

  async function act(actionType: BriefAction) {
    setActionMessage("");
    setPendingAction(actionType);
    try {
      await apiRequest(`/api/v1/briefs/${id}/actions`, { method: "POST", body: JSON.stringify({ action_type: actionType }) });
      setActionMessage(`${actions.find(([value]) => value === actionType)?.[1]} recorded.`);
      await load();
    } catch (error) {
      setActionMessage(friendlyError(error, "We couldn't record this action. Try again."));
    } finally { setPendingAction(null); }
  }

  function openEvidence() {
    setShowEvidence((value) => !value);
    if (!showEvidence) void recordProductEvent("EVIDENCE_PANEL_OPENED", { object_type: "DECISION_BRIEF", object_id: id });
  }

  return <WorkspaceShell><section className="detail-page">
    <Link className="text-link detail-back" href="/briefing">Back to briefing</Link>
    {state.status === "loading" && <ModuleLoading label="Loading Decision Brief" />}
    {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
    {state.status === "ready" && <div className="decision-brief-grid"><article className="brief-detail brief-detail-v2">
      <header><div className="brief-meta"><span className={`priority-chip priority-${state.data.relevance_band.toLowerCase()}`}>{state.data.relevance_band}</span><span>{readable(state.data.primary_domain)}</span>{Number(state.data.material_change_count ?? 0) > 0 && <span className="updated-chip">Updated</span>}</div><h1>{state.data.what_changed}</h1><p className="brief-deck">{state.data.why_it_matters || "Stem is retaining this development for a bounded decision review."}</p></header>
      <section><p className="section-kicker">01</p><h2>What changed</h2><p>{state.data.what_changed}</p></section>
      <section><p className="section-kicker">02</p><h2>Why it matters to you</h2><p>{state.data.why_it_matters || "No company-specific assertion is available beyond the verified evidence."}</p></section>
      <section className="split-evidence"><div><p className="section-kicker">03</p><h2>Business exposure</h2><p>{state.data.exposure_summary || "Exposure is still being assessed."}</p><div className="brief-chip-row">{state.data.exposure_types?.map((item) => <span key={item}>{readable(item)}</span>)}</div></div><div><p className="section-kicker">04</p><h2>Stakes</h2><p>{state.data.stakes_summary || "No quantified stake has been verified."}</p><div className="brief-chip-row">{state.data.stakes_types?.map((item) => <span className="stakes-chip" key={item}>{readable(item)}</span>)}</div></div></section>
      <section className="decision-callout"><p className="section-kicker">05</p><h2>Decision required</h2><p>{state.data.decision_prompt || "Continue monitoring while the remaining evidence develops."}</p></section>
      <section><div className="section-heading"><div><p className="section-kicker">06</p><h2>Decision Paths</h2></div>{state.data.guidance_status && <span>{readable(state.data.guidance_status)}</span>}</div><p>{state.data.gaps_summary}</p>{state.data.response_options?.length ? <div className="decision-paths">{state.data.response_options.map((option) => <article key={option.option_code}><small>{option.option_code}</small><h3>{option.title}</h3><p>{option.description}</p>{option.tradeoffs?.map((tradeoff) => <span key={tradeoff}>{tradeoff}</span>)}</article>)}</div> : <p className="quiet-state">Stem needs more verified Company Context before presenting bounded response options.</p>}{state.data.next_validation_steps?.length ? <div className="validation-steps"><h3>Validate next</h3><ol>{state.data.next_validation_steps.map((step) => <li key={step}>{step}</li>)}</ol></div> : null}</section>
      <section><button aria-expanded={showEvidence} className="evidence-toggle" onClick={openEvidence} type="button"><span><span className="section-kicker">07</span><strong>Evidence</strong><small>{state.data.evidence?.length ?? 0} verified item{state.data.evidence?.length === 1 ? "" : "s"}</small></span><b>{showEvidence ? "Hide" : "Review"}</b></button>{showEvidence && <ul className="evidence-list">{state.data.evidence?.map((item) => <li key={item.id}><div><strong>{item.title || item.source_name}</strong><small>{item.source_name} / {item.confidence_band || "Reviewed"}</small></div>{item.source_url && <a href={item.source_url} rel="noreferrer" target="_blank">Open source</a>}</li>)}</ul>}</section>
      {state.data.timeline?.length ? <section><p className="section-kicker">08</p><h2>Brief history</h2><ol className="brief-timeline">{state.data.timeline.map((event, index) => <li key={`${event.event_type}-${index}`}><span /><div><strong>{readable(event.event_type)}</strong><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></div></li>)}</ol></section> : null}
    </article><aside className="brief-context-rail"><section><p className="eyebrow">Decision context</p><dl><div><dt>Status</dt><dd>{readable(state.data.brief_status)}</dd></div><div><dt>Owner</dt><dd>{state.data.owner_roles?.join(", ") || "Leadership"}</dd></div><div><dt>Confidence</dt><dd>{readable(state.data.confidence_band) || "Reviewed"}</dd></div><div><dt>Decision window</dt><dd>{state.data.decision_window || "Monitor"}</dd></div><div><dt>Why shown</dt><dd>{state.data.personal_priority_score ? `${Math.round(Number(state.data.personal_priority_score) * 100)}% Decision Lens match` : "Company priority"}</dd></div></dl></section><button className="primary-button investigate-button" onClick={() => { setShowCil(true); void recordProductEvent("CIL_OPENED", { object_type: "DECISION_BRIEF", object_id: id }); }} type="button">Investigate with Cogent</button><div className="rail-actions">{actions.map(([value, label]) => <button disabled={pendingAction !== null} key={value} onClick={() => void act(value)} type="button">{pendingAction === value ? "Saving..." : label}</button>)}</div>{actionMessage && <p aria-live="polite" className="form-message">{actionMessage}</p>}{showCil && <CILPanel anchorId={id} />}</aside></div>}
  </section></WorkspaceShell>;
}
