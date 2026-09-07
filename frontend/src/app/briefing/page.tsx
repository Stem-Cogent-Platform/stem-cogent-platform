"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { BriefCard } from "@/components/brief-card";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { accessToken, apiRequest, bootstrapSession, currentUser } from "@/lib/api";
import { friendlyError, stateMessages } from "@/lib/product-copy/stateMessages";
import { Brief, LoadState } from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

type MonitoringItem = {
  id: string;
  display_title: string;
  signal_id?: string;
  what_changed: string;
  primary_domain?: string;
  event_type?: string;
  primary_entity?: string;
  matched_company_objects: string[];
  published_at?: string;
  detected_at: string;
  evidence_available: boolean;
  source_url?: string;
  source_name: string;
};
type BriefingData = {
  briefs: Brief[];
  monitoring: MonitoringItem[];
  changes: { new_briefs: number; updated_briefs: number; new_evidence_items: number; new_relevant_monitoring: number; as_of?: string; since_known?: boolean };
  phase5UiEnabled: boolean;
  readiness: { state: string; message?: string | null; last_checked_at?: string | null };
};

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function relativeTime(value: string) {
  const minutes = Math.max(1, Math.round((Date.now() - new Date(value).getTime()) / 60_000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  return hours < 24 ? `${hours}h ago` : `${Math.round(hours / 24)}d ago`;
}

export default function BriefingPage() {
  const [state, setState] = useState<LoadState<BriefingData>>({ status: "loading" });
  const [connection, setConnection] = useState("Connecting");
  const [newCount, setNewCount] = useState(0);

  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      const capabilities = await apiRequest<{ phase5_new_ui_enabled: boolean }>("/api/v1/capabilities");
      // Snapshot the visit watermark before loading the items that will be rendered.
      const changes = capabilities.phase5_new_ui_enabled
        ? await apiRequest<BriefingData["changes"]>("/api/v1/briefing/changes")
        : { new_briefs: 0, updated_briefs: 0, new_evidence_items: 0, new_relevant_monitoring: 0 };
      const [briefs, monitoring, readiness] = await Promise.all([
        apiRequest<Brief[]>("/api/v1/briefs"),
        capabilities.phase5_new_ui_enabled ? apiRequest<MonitoringItem[]>("/api/v1/relevant-monitoring?limit=8") : Promise.resolve([]),
        capabilities.phase5_new_ui_enabled ? apiRequest<BriefingData["readiness"]>("/api/v1/briefing/readiness") : Promise.resolve({ state: "LEGACY" }),
      ]);
      if (readiness.state === "PREPARE_REQUIRED") {
        const preparation = await apiRequest<{ state: string }>("/api/v1/briefing/prepare", { method: "POST" });
        readiness.state = preparation.state;
      }
      setState({ status: "ready", data: { briefs, monitoring, changes, readiness, phase5UiEnabled: capabilities.phase5_new_ui_enabled } });
      setNewCount(0);
    } catch (error) {
      setState({ status: "error", message: friendlyError(error, "We couldn't load this briefing. Try again.") });
    }
  }, []);

  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  useEffect(() => {
    let reconnect: ReturnType<typeof setTimeout> | undefined;
    let active = true;
    let socket: WebSocket | undefined;
    let reconnectAttempt = 0;
    function connect() {
      if (!active) return;
      const token = accessToken();
      if (!token) { setConnection("Updates paused"); return; }
      socket = new WebSocket(`${WS_URL.replace(/\/$/, "")}/api/v1/realtime/briefing?access_token=${encodeURIComponent(token)}`);
      socket.onopen = () => { reconnectAttempt = 0; setConnection("Updates connected"); };
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (["NEW_BRIEF", "BRIEF_CREATED", "BRIEF_UPDATED", "RELEVANT_MONITORING_ADDED", "PERSONALISATION_COMPLETED"].includes(message.type)) {
            void apiRequest<BriefingData["changes"]>("/api/v1/briefing/changes").then((changes) => setNewCount(changes.new_briefs + changes.updated_briefs + changes.new_relevant_monitoring)).catch(() => setConnection("Updates delayed"));
          }
        } catch { /* Non-contract frames are ignored. */ }
      };
      socket.onerror = () => setConnection("Updates delayed");
      socket.onclose = () => {
        setConnection("Reconnecting");
        if (active) reconnect = setTimeout(connect, Math.min(30_000, 1_000 * (2 ** reconnectAttempt++)));
      };
    }
    void bootstrapSession().then((authenticated) => authenticated && connect());
    return () => { active = false; if (reconnect) clearTimeout(reconnect); socket?.close(); };
  }, []);

  const firstName = String(currentUser()?.display_name ?? "").trim().split(/\s+/)[0];
  const data = state.status === "ready" ? state.data : null;

  const prepared = data && ["ASSESSED", "NO_RECENT_MATCH", "LEGACY"].includes(data.readiness.state);
  useEffect(() => {
    if (!data || !["PREPARING", "PREPARE_REQUIRED"].includes(data.readiness.state)) return;
    const timer = window.setTimeout(() => void load(), 3000);
    return () => window.clearTimeout(timer);
  }, [data, load]);
  useEffect(() => {
    if (!prepared || !data?.changes.as_of) return;
    const through = data.changes.as_of;
    const frame = window.requestAnimationFrame(() => {
      void apiRequest("/api/v1/briefing/viewed", { method: "POST", body: JSON.stringify({ viewed_through: through }) }).catch(() => undefined);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [prepared, data]);

  if (data && !data.phase5UiEnabled) {
    return <WorkspaceShell><section className="content-page"><section className="briefing-heading"><div><p className="eyebrow">My Decision Briefing</p><h1>Developments requiring attention</h1></div><span className="connection-status"><i /> {connection}</span></section>{newCount > 0 && <button className="new-brief-banner" onClick={() => void load()} type="button">{newCount} new brief{newCount === 1 ? " is" : "s are"} ready</button>}<section className="briefing-grid"><div className="brief-column"><div className="section-heading"><h2>Decision briefs</h2><span>{data.briefs.length} evidence-backed</span></div>{data.briefs.map((brief) => <BriefCard brief={brief} key={brief.id} phase5Ui={false} />)}{!data.briefs.length && <article className="empty-brief"><h3>No developments currently meet your Decision Brief threshold.</h3><p>Wider Intelligence remains available while Stem continues monitoring your Focus Areas.</p><Link className="secondary-button" href="/intelligence">Review Wider Intelligence</Link></article>}</div><aside className="focus-panel"><p className="eyebrow">Watching</p><h2>Your Focus Areas</h2><p>Your configured Focus Areas influence ranking while factual evidence remains shared and unchanged.</p><Link className="text-link" href="/watchlist">Review focus and watchlist</Link></aside></section></section></WorkspaceShell>;
  }

  return <WorkspaceShell>
    {data && !prepared && <section className="content-page">
      {data.readiness.state === "PREPARATION_DELAYED"
        ? <ModuleFailure message="Your setup is saved. Briefing preparation is delayed." retry={() => { void apiRequest("/api/v1/briefing/prepare", { method: "POST" }).then(() => load()); }} />
        : <ModuleLoading label="Preparing your briefing" />}
    </section>}
    {data?.readiness.message && <section className="content-page"><p className="form-message" role="status">{data.readiness.message}</p></section>}
    <section className="briefing-heading briefing-heading-v2"><div><p className="eyebrow">My Decision Briefing</p><h1>{greeting()}{firstName ? `, ${firstName}` : ""}</h1>{prepared && <p className="briefing-lead"><strong>{data.briefs.length}</strong> decision{data.briefs.length === 1 ? "" : "s"} require your attention <span /> <strong>{data.monitoring.length}</strong> relevant development{data.monitoring.length === 1 ? " is" : "s are"} being monitored</p>}</div><span className="page-status" title={connection}>Monitoring</span></section>
    {newCount > 0 && <button aria-live="polite" className="new-brief-banner" onClick={() => void load()} type="button">{newCount} briefing update{newCount === 1 ? "" : "s"} ready to review</button>}
    {state.status === "loading" && <section className="content-page briefing-loading"><ModuleLoading label="Preparing your briefing" /></section>}
    {state.status === "error" && <section className="content-page"><ModuleFailure message={state.message} retry={() => void load()} /></section>}
    {prepared && <section className="briefing-v2"><div className="briefing-main">
      <section aria-labelledby="attention-title"><div className="section-heading"><div><p className="eyebrow">Requires your attention</p><h2 id="attention-title">Material decisions</h2></div><span>{data.briefs.length} open</span></div><div className="card-list">{data.briefs.map((brief) => <BriefCard brief={brief} key={brief.id} />)}</div>{!data.briefs.length && <article className="empty-brief"><h3>{stateMessages.briefingEmpty.title}</h3><p>{data.readiness.state === "ASSESSED" ? stateMessages.briefingEmpty.body : "Stem is monitoring your configured scope. No verified recent development currently matches strongly enough to require action."}</p><Link className="secondary-button" href="/intelligence">Explore Wider Intelligence</Link></article>}</section>
      <section aria-labelledby="monitoring-title" className="monitoring-section"><div className="section-heading"><div><p className="eyebrow">Relevant monitoring</p><h2 id="monitoring-title">Below the decision threshold</h2></div><Link href="/intelligence">Wider Intelligence -&gt;</Link></div><div className="monitoring-list">{data.monitoring.map((item) => <article key={item.id}><div><span>{item.primary_domain?.replaceAll("_", " ") ?? "Market development"}{item.event_type ? ` · ${item.event_type.replaceAll("_", " ")}` : ""}{item.primary_entity ? ` · ${item.primary_entity}` : ""}</span><h3>{item.signal_id ? <Link href={`/signals/${item.signal_id}`}>{item.display_title}</Link> : item.display_title}</h3><p>{item.matched_company_objects.length ? `Relevant to ${item.matched_company_objects.slice(0, 2).join(" and ")}` : item.what_changed}</p><small>{item.evidence_available ? `${item.source_name} · Evidence available` : "Evidence is still being verified"}</small></div><time dateTime={item.published_at ?? item.detected_at}>{relativeTime(item.published_at ?? item.detected_at)}</time>{item.evidence_available && item.source_url && <a href={item.source_url} rel="noreferrer" target="_blank">Open evidence</a>}</article>)}</div>{!data.monitoring.length && <p className="quiet-state">No additional verified recent developments match your configured scope.</p>}</section>
    </div><aside className="briefing-rail"><section className="since-visit"><p className="eyebrow">Since your last visit</p><strong>{data.changes.since_known === false ? "Your first briefing visit" : `${data.changes.new_briefs + data.changes.new_relevant_monitoring} new developments`}</strong><span>{data.changes.updated_briefs} brief updated / {data.changes.new_evidence_items} new evidence item{data.changes.new_evidence_items === 1 ? "" : "s"}</span>{data.changes.new_relevant_monitoring > 0 && <small>{data.changes.new_relevant_monitoring} monitoring update{data.changes.new_relevant_monitoring === 1 ? "" : "s"}</small>}</section><section className="focus-panel"><p className="eyebrow">Your lens</p>{data.readiness.last_checked_at && <p>Last monitoring check: {relativeTime(data.readiness.last_checked_at)}</p>}<h2>Focus Area activity</h2><p>Your Company Context and personal Focus Areas shape ranking without changing the underlying evidence.</p><Link className="text-link" href="/watchlist">Review Focus Areas</Link></section></aside></section>}
  </WorkspaceShell>;
}
