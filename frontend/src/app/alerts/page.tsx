"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest, recordProductEvent } from "@/lib/api";
import { stateMessages } from "@/lib/product-copy/stateMessages";
import { LoadState } from "@/lib/types";

type Alert = {
  id: string;
  brief_id: string;
  priority: string;
  subject: string;
  status: string;
  read_at?: string;
  created_at: string;
  payload: { why_delivered?: string };
};

export default function AlertsPage() {
  const router = useRouter();
  const [state, setState] = useState<LoadState<Alert[]>>({ status: "loading" });
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");

  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      setState({ status: "ready", data: await apiRequest<Alert[]>("/api/v1/alerts") });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Alerts could not be loaded." });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function open(item: Alert) {
    setOpeningId(item.id);
    setActionError("");
    try {
      if (!item.read_at) {
        await apiRequest(`/api/v1/alerts/${item.id}/read`, { method: "POST" });
      }
      void recordProductEvent("ALERT_OPENED", { object_type: "ALERT", object_id: item.id });
      router.push(`/briefs/${item.brief_id}`);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "This alert could not be opened.");
      setOpeningId(null);
    }
  }

  return (
    <WorkspaceShell>
      <section className="content-page">
        <div className="page-heading">
          <div><p className="eyebrow">Decision Brief notifications</p><h1>Alerts</h1></div>
        </div>
        {state.status === "loading" && <ModuleLoading label="Loading alerts" />}
        {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
        {state.status === "ready" && (
          <div className="alert-list">
            {actionError && <p className="form-message" role="alert">{actionError}</p>}
            {state.data.map((item) => (
              <article className={item.read_at ? "" : "unread"} key={item.id}>
                <span className={`priority-chip priority-${item.priority.toLowerCase()}`}>{item.priority}</span>
                <div><h2>{item.subject}</h2><p>{item.payload?.why_delivered || "Matched your configured Decision Lens."}</p></div>
                <button className="text-link" disabled={openingId === item.id} onClick={() => void open(item)} type="button">
                  {openingId === item.id ? "Opening…" : "Open brief"}
                </button>
              </article>
            ))}
            {!state.data.length && (
              <section className="empty-brief">
                <h2>{stateMessages.alertsEmpty.title}</h2>
                <p>{stateMessages.alertsEmpty.body}</p>
                <Link href="/briefing">Return to briefing</Link>
              </section>
            )}
          </div>
        )}
      </section>
    </WorkspaceShell>
  );
}
