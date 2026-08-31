"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type WatchItem = { id: string; name: string; object_type: string; importance: string; entity_id?: string; recent_activity_count: number | null; open_brief_count: number };
type FocusItem = { id: string; label: string; focus_type: string; weight: number; entity_id?: string; recent_activity_count: number | null; open_brief_count: number | null };
type Watchlist = { company: WatchItem[]; focus: FocusItem[] };

function Activity({ count }: { count: number | null }) {
  return <span>{count === null ? "Entity link needed" : `${count} signal${count === 1 ? "" : "s"} · 30 days`}</span>;
}

export default function WatchlistPage() {
  const [state, setState] = useState<LoadState<Watchlist>>({ status: "loading" });
  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      setState({ status: "ready", data: await apiRequest<Watchlist>("/api/v1/watchlist") });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Your watchlist could not be loaded." });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  return (
    <WorkspaceShell>
      <section className="content-page">
        <div className="page-heading"><div><p className="eyebrow">Monitoring scope</p><h1>Watchlist & Focus Areas</h1></div><Link className="secondary-button" href="/onboarding/lens">Add a Focus Area</Link></div>
        {state.status === "loading" && <ModuleLoading label="Loading watchlist and Focus Areas" />}
        {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
        {state.status === "ready" && (
          <div className="two-column">
            <section className="panel">
              <h2>Company watchlist</h2>
              {state.data.company.map((item) => <article className="watch-item" key={item.id}><div><small>{item.object_type.replaceAll("_", " ")}</small><strong>{item.name}</strong><Activity count={item.recent_activity_count} /></div><span>{item.open_brief_count} open brief{item.open_brief_count === 1 ? "" : "s"}</span>{item.entity_id && <Link href={`/entities/${item.entity_id}`}>View entity</Link>}</article>)}
              {!state.data.company.length && <p>The watchlist query completed successfully. No Company Context objects are configured.</p>}
            </section>
            <section className="panel">
              <h2>My Focus Areas</h2>
              {state.data.focus.map((item) => <article className="watch-item" key={item.id}><div><small>{item.focus_type.replaceAll("_", " ")}</small><strong>{item.label}</strong><Activity count={item.recent_activity_count} /></div><span>{Math.round(Number(item.weight) * 100)}% weight</span>{item.entity_id && <Link href={`/entities/${item.entity_id}`}>View entity</Link>}</article>)}
              {!state.data.focus.length && <p>The Focus Areas query completed successfully. Configure a Focus Area to personalise your briefing.</p>}
              {state.data.focus.some((item) => item.open_brief_count === null) && <p className="data-caveat">Personal Focus Area-to-brief linkage is not persisted by the current decision worker, so an open-brief count is not shown.</p>}
            </section>
          </div>
        )}
      </section>
    </WorkspaceShell>
  );
}
