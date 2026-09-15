"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";
import { stateMessages } from "@/lib/product-copy/stateMessages";

type Digest = {
  id: string;
  period_start: string;
  period_end: string;
  status: string;
  brief_ids: string[];
  briefs?: { id: string; what_changed: string; status: string }[];
  content: { latest_brief?: { what_changed: string; priority: string } };
};

export default function DigestsPage() {
  const [state, setState] = useState<LoadState<Digest[]>>({ status: "loading" });
  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      setState({ status: "ready", data: await apiRequest<Digest[]>("/api/v1/digests") });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Digests could not be loaded." });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  return (
    <WorkspaceShell>
      <section className="content-page">
        <div className="page-heading"><div><p className="eyebrow">Decisions requiring attention first</p><h1>Digests</h1></div></div>
        {state.status === "loading" && <ModuleLoading label="Loading digests" />}
        {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
        {state.status === "ready" && (
          <div className="intelligence-list">
            {state.data.map((item) => (
              <article key={item.id}>
                <div className="brief-meta"><span>{new Date(item.period_start).toLocaleDateString()} – {new Date(new Date(item.period_end).getTime() - 1).toLocaleDateString()}</span><span>{item.status === "READY" ? "Ready to read" : item.status}</span></div>
                <h2>{item.content.latest_brief?.what_changed || "Decision Brief digest"}</h2>
                <p>{item.brief_ids.length} brief{item.brief_ids.length === 1 ? "" : "s"} included.</p>
                <ul>{item.briefs?.map((brief) => <li key={brief.id}><Link href={`/briefs/${brief.id}`} prefetch={false}>{brief.what_changed}</Link></li>)}</ul>
              </article>
            ))}
            {!state.data.length && (
              <section className="empty-brief">
                <p className="eyebrow">Your briefing digest</p>
                <h2>{stateMessages.digestEmpty.title}</h2>
                <p>{stateMessages.digestEmpty.body}</p>
                <ul><li>Decisions requiring attention</li><li>Unresolved watched briefs</li><li>Important Focus Area changes</li><li>Selected Wider Intelligence</li></ul>
                <Link href="/settings">Digest settings</Link>
              </section>
            )}
          </div>
        )}
      </section>
    </WorkspaceShell>
  );
}
