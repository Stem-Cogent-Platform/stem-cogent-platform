"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CILPanel } from "@/components/cil-panel";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { Brief, LoadState } from "@/lib/types";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const actions = [
  ["ACKNOWLEDGED", "Acknowledge"],
  ["WATCHING", "Watch"],
  ["ESCALATED", "Escalate"],
  ["ACTED_ON", "Acted on"],
  ["DISMISSED", "Dismiss"]
] as const;

export default function BriefDetailPage() {
  const id = String(useParams<{ briefId: string }>().briefId ?? "");
  const [state, setState] = useState<LoadState<Brief>>(
    UUID.test(id) ? { status: "loading" } : { status: "error", message: "This Decision Brief link is not valid." }
  );
  const [actionMessage, setActionMessage] = useState("");
  const [pendingAction, setPendingAction] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!UUID.test(id)) return;
    try {
      setState({ status: "loading" });
      setState({ status: "ready", data: await apiRequest<Brief>(`/api/v1/briefs/${id}`) });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "This Decision Brief could not be loaded." });
    }
  }, [id]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function act(actionType: string) {
    setActionMessage("");
    setPendingAction(actionType);
    try {
      await apiRequest(`/api/v1/briefs/${id}/actions`, {
        method: "POST",
        body: JSON.stringify({ action_type: actionType })
      });
      setActionMessage("Your decision action is recorded in the audit trail.");
      await load();
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "We could not record this action.");
    } finally {
      setPendingAction(null);
    }
  }

  return (
    <WorkspaceShell>
      <section className="detail-page">
        <Link className="text-link" href="/briefing">← Back to briefing</Link>
        {state.status === "loading" && <ModuleLoading label="Loading Decision Brief" />}
        {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
        {state.status === "ready" && (
          <div className="detail-grid brief-detail-layout">
            <article className="brief-detail">
              <div className="brief-meta">
                <span className={`priority-chip priority-${state.data.relevance_band.toLowerCase()}`}>{state.data.relevance_band}</span>
                <span>{state.data.confidence_band} confidence</span>
                <span>{state.data.quantification_status.replaceAll("_", " ")}</span>
              </div>
              <h1>{state.data.what_changed}</h1>
              <section><h2>Why it matters to you</h2><p>{state.data.why_it_matters || "No company-specific assertion is available beyond the verified evidence."}</p></section>
              <section><h2>Exposure and stakes</h2><p>{state.data.exposure_summary || "Exposure is still being assessed."}</p><p>{state.data.stakes_summary || "No quantified stake has been verified."}</p></section>
              <section><h2>Decision required</h2><p>{state.data.decision_prompt || "Continue monitoring this development."}</p><p><strong>Owner:</strong> {state.data.owner_roles.join(", ") || "Unassigned"}</p></section>
              <section><h2>Uncertainty</h2>{state.data.uncertainties.length ? <ul>{state.data.uncertainties.map((item) => <li key={item}>{item.replaceAll("_", " ")}</li>)}</ul> : <p>No additional uncertainty was recorded.</p>}</section>
              <section>
                <h2>Evidence</h2>
                <ul className="evidence-list">
                  {state.data.evidence?.map((item) => (
                    <li key={item.id}>
                      <div><strong>{item.title || item.source_name}</strong><small>{item.source_name} · {item.confidence_band || "Reviewed"}</small></div>
                      {item.source_url && <a href={item.source_url} rel="noreferrer" target="_blank">Open source</a>}
                    </li>
                  ))}
                </ul>
              </section>
              <section className="decision-actions">
                <h2>Record decision action</h2>
                <div>
                  {actions.map(([value, label]) => (
                    <button disabled={pendingAction !== null} key={value} onClick={() => void act(value)} type="button">
                      {pendingAction === value ? "Recording…" : label}
                    </button>
                  ))}
                </div>
                {actionMessage && <p aria-live="polite" className="form-message">{actionMessage}</p>}
              </section>
            </article>
            <CILPanel anchorId={id} />
          </div>
        )}
      </section>
    </WorkspaceShell>
  );
}
