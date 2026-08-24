"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type Watch = { objects: { id: string; name: string; object_type: string; importance: string; entity_id?: string }[] };
type Focus = { id: string; label: string; focus_type: string; weight: number; entity_id?: string };
export default function WatchlistPage() {
  const [state, setState] = useState<LoadState<{ watch: Watch; focus: Focus[] }>>({ status: "loading" });
  const load = useCallback(async () => { try { const [watch, focus] = await Promise.all([apiRequest<Watch>("/context/company"), apiRequest<Focus[]>("/me/focus-areas")]); setState({ status: "ready", data: { watch, focus } }); } catch (error) { setState({ status: "error", message: error instanceof Error ? error.message : "Your watchlist could not be loaded." }); } }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  return <WorkspaceShell><section className="content-page"><div className="page-heading"><div><p className="eyebrow">Monitoring scope</p><h1>Watchlist & Focus Areas</h1></div><Link className="secondary-button" href="/onboarding/lens">Add a Focus Area</Link></div>{state.status === "loading" && <ModuleLoading />}{state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}{state.status === "ready" && <div className="two-column"><section className="panel"><h2>Company watchlist</h2>{state.data.watch.objects.map((item) => <article className="watch-item" key={item.id}><div><small>{item.object_type.replaceAll("_", " ")}</small><strong>{item.name}</strong></div><span>{item.importance}</span>{item.entity_id && <Link href={`/entities/${item.entity_id}`}>View entity</Link>}</article>)}{!state.data.watch.objects.length && <p>No company objects are configured yet.</p>}</section><section className="panel"><h2>My Focus Areas</h2>{state.data.focus.map((item) => <article className="watch-item" key={item.id}><div><small>{item.focus_type.replaceAll("_", " ")}</small><strong>{item.label}</strong></div><span>{Math.round(Number(item.weight) * 100)}% weight</span></article>)}{!state.data.focus.length && <p>Configure a Focus Area to personalise your briefing.</p>}</section></div>}</section></WorkspaceShell>;
}
