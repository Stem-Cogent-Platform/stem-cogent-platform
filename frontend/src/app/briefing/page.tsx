"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { BriefCard } from "@/components/brief-card";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { accessToken, apiRequest } from "@/lib/api";
import { Brief, LoadState } from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export default function BriefingPage() {
  const [briefs, setBriefs] = useState<LoadState<Brief[]>>({ status: "loading" });
  const [connection, setConnection] = useState("Connecting");
  const [newCount, setNewCount] = useState(0);

  const load = useCallback(async () => {
    try {
      setBriefs({ status: "ready", data: await apiRequest<Brief[]>("/api/v1/briefs") });
      setNewCount(0);
    } catch (error) {
      setBriefs({ status: "error", message: error instanceof Error ? error.message : "Your briefing could not be loaded." });
    }
  }, []);

  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  useEffect(() => {
    const token = accessToken();
    if (!token) return;
    let reconnect: ReturnType<typeof setTimeout> | undefined;
    let active = true;
    let socket: WebSocket;
    function connect() {
      if (!active) return;
      socket = new WebSocket(`${WS_URL.replace(/\/$/, "")}/api/v1/realtime/briefing?access_token=${encodeURIComponent(accessToken() ?? "")}`);
      socket.onopen = () => setConnection("Connected");
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "NEW_BRIEF") setNewCount((value) => value + 1);
        } catch { /* Ignore non-contract frames. */ }
      };
      socket.onerror = () => setConnection("Updates delayed");
      socket.onclose = () => {
        setConnection("Reconnecting");
        if (active) reconnect = setTimeout(connect, 4000);
      };
    }
    connect();
    return () => { active = false; if (reconnect) clearTimeout(reconnect); socket?.close(); };
  }, []);

  const data = briefs.status === "ready" ? briefs.data : [];
  return (
    <WorkspaceShell>
      <section className="briefing-heading">
        <div><p className="eyebrow">My Decision Briefing</p><h1>Developments requiring attention</h1></div>
        <span className="connection-status"><i /> {connection}</span>
      </section>
      {newCount > 0 && <button className="new-brief-banner" onClick={() => void load()} type="button">{newCount} new brief{newCount === 1 ? " is" : "s are"} ready — review updates</button>}
      <section className="briefing-grid">
        <div className="brief-column">
          <div className="section-heading"><h2>Priority briefs</h2><span>{data.length} evidence-backed</span></div>
          {briefs.status === "loading" && <ModuleLoading label="Loading Decision Briefs" />}
          {briefs.status === "error" && <ModuleFailure message={briefs.message} retry={() => void load()} />}
          {briefs.status === "ready" && data.length === 0 && (
            <article className="empty-brief"><h3>No developments currently meet your Decision Brief threshold.</h3><p>Wider Intelligence remains available while Stem continues monitoring your Focus Areas.</p><Link className="secondary-button" href="/intelligence">Review Wider Intelligence</Link></article>
          )}
          {data.map((brief) => <BriefCard brief={brief} key={brief.id} />)}
        </div>
        <aside className="focus-panel"><p className="eyebrow">Watching</p><h2>Your Focus Areas</h2><p>Your configured Focus Areas influence ranking while factual evidence remains shared and unchanged.</p><Link className="text-link" href="/watchlist">Review focus and watchlist</Link></aside>
      </section>
    </WorkspaceShell>
  );
}
