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

type MonitoringItem = { id: string; headline: string; relevance_reasons?: string[]; primary_domain?: string; detected_at: string };
type BriefingData = {
  briefs: Brief[];
  monitoring: MonitoringItem[];
  changes: { new_briefs: number; updated_briefs: number; new_evidence_items: number; new_relevant_monitoring: number };
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
      const [briefs, monitoring, changes] = await Promise.all([
        apiRequest<Brief[]>("/api/v1/briefs"),
        apiRequest<MonitoringItem[]>("/api/v1/relevant-monitoring?limit=8"),
        apiRequest<BriefingData["changes"]>("/api/v1/briefing/changes")
      ]);
      setState({ status: "ready", data: { briefs, monitoring, changes } });
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
      socket.onopen = () => { reconnectAttempt = 0; setConnection("Live"); };
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (["NEW_BRIEF", "BRIEF_CREATED", "BRIEF_UPDATED"].includes(message.type)) setNewCount((value) => value + 1);
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

  return <WorkspaceShell>
    <section className="briefing-heading briefing-heading-v2"><div><p className="eyebrow">My Decision Briefing</p><h1>{greeting()}{firstName ? `, ${firstName}` : ""}</h1>{data && <p className="briefing-lead"><strong>{data.briefs.length}</strong> decision{data.briefs.length === 1 ? "" : "s"} require your attention <span /> <strong>{data.monitoring.length}</strong> relevant development{data.monitoring.length === 1 ? " is" : "s are"} being monitored</p>}</div><span className="page-status"><i />{connection}</span></section>
    {newCount > 0 && <button aria-live="polite" className="new-brief-banner" onClick={() => void load()} type="button">{newCount} briefing update{newCount === 1 ? "" : "s"} ready to review</button>}
    {state.status === "loading" && <section className="content-page briefing-loading"><ModuleLoading label="Preparing your briefing" /></section>}
    {state.status === "error" && <section className="content-page"><ModuleFailure message={state.message} retry={() => void load()} /></section>}
    {data && <section className="briefing-v2"><div className="briefing-main">
      <section aria-labelledby="attention-title"><div className="section-heading"><div><p className="eyebrow">Requires your attention</p><h2 id="attention-title">Material decisions</h2></div><span>{data.briefs.length} open</span></div><div className="card-list">{data.briefs.map((brief) => <BriefCard brief={brief} key={brief.id} />)}</div>{!data.briefs.length && <article className="empty-brief"><h3>{stateMessages.briefingEmpty.title}</h3><p>{stateMessages.briefingEmpty.body}</p><Link className="secondary-button" href="/intelligence">Explore Wider Intelligence</Link></article>}</section>
      <section aria-labelledby="monitoring-title" className="monitoring-section"><div className="section-heading"><div><p className="eyebrow">Relevant monitoring</p><h2 id="monitoring-title">Below the decision threshold</h2></div><Link href="/intelligence">Wider Intelligence -&gt;</Link></div><div className="monitoring-list">{data.monitoring.map((item) => <article key={item.id}><div><span>{item.primary_domain?.replaceAll("_", " ") ?? "Market development"}</span><h3>{item.headline}</h3><p>Monitoring{item.relevance_reasons?.length ? ` / ${item.relevance_reasons.slice(0, 2).join(" / ")}` : " / Relevant to your context"}</p></div><time dateTime={item.detected_at}>{relativeTime(item.detected_at)}</time></article>)}</div>{!data.monitoring.length && <p className="quiet-state">No additional developments are being monitored for your current lens.</p>}</section>
    </div><aside className="briefing-rail"><section className="since-visit"><p className="eyebrow">Since your last visit</p><strong>{data.changes.new_briefs} new development{data.changes.new_briefs === 1 ? "" : "s"}</strong><span>{data.changes.updated_briefs} brief updated / {data.changes.new_evidence_items} new evidence item{data.changes.new_evidence_items === 1 ? "" : "s"}</span>{data.changes.new_relevant_monitoring > 0 && <small>{data.changes.new_relevant_monitoring} monitoring update{data.changes.new_relevant_monitoring === 1 ? "" : "s"}</small>}</section><section className="focus-panel"><p className="eyebrow">Your lens</p><h2>Focus Area activity</h2><p>Your Company Context and personal Focus Areas shape ranking without changing the underlying evidence.</p><Link className="text-link" href="/watchlist">Review Focus Areas</Link></section></aside></section>}
  </WorkspaceShell>;
}
