"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest, recordProductEvent } from "@/lib/api";
import { stateMessages } from "@/lib/product-copy/stateMessages";
import { LoadState } from "@/lib/types";

type WatchItem = { id: string; name: string; object_type: string; importance: string; entity_id?: string; recent_activity_count: number | null; open_brief_count: number };
type FocusItem = { id: string; label: string; focus_type: string; weight?: number; entity_id?: string; recent_activity_count: number | null; open_brief_count: number | null };
type Watchlist = { company: WatchItem[]; focus: FocusItem[] };
const tabs = ["COMPETITOR", "PRODUCT", "DEPENDENCY", "MARKET", "REGULATOR", "FOCUS"] as const;

export default function WatchlistPage() {
  const [state, setState] = useState<LoadState<Watchlist>>({ status: "loading" });
  const [phase5Ui, setPhase5Ui] = useState(false);
  const [tab, setTab] = useState<(typeof tabs)[number]>("COMPETITOR");
  const load = useCallback(async () => { try { setState({ status: "loading" }); const [data, capabilities] = await Promise.all([apiRequest<Watchlist>("/api/v1/watchlist"), apiRequest<{ phase5_new_ui_enabled: boolean }>("/api/v1/capabilities")]); setPhase5Ui(capabilities.phase5_new_ui_enabled); setState({ status: "ready", data }); } catch (error) { setState({ status: "error", message: error instanceof Error ? error.message : "Your watchlist could not be loaded." }); } }, []);
  useEffect(() => { const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [load]);
  const items = useMemo(() => state.status !== "ready" ? [] : tab === "FOCUS" ? state.data.focus : state.data.company.filter((item) => item.object_type === tab), [state, tab]);

  if (state.status === "ready" && !phase5Ui) {
    return <WorkspaceShell><section className="content-page"><div className="page-heading"><div><p className="eyebrow">Monitoring scope</p><h1>Watchlist & Focus Areas</h1></div><Link className="secondary-button" href="/onboarding/lens">Add a Focus Area</Link></div><div className="two-column"><section className="panel"><h2>Company watchlist</h2>{state.data.company.map((item) => <article className="watch-item" key={item.id}><div><small>{item.object_type.replaceAll("_", " ")}</small><strong>{item.name}</strong><span>{item.recent_activity_count == null ? "Monitoring setup in progress" : `${item.recent_activity_count} signal${item.recent_activity_count === 1 ? "" : "s"} · 30 days`}</span></div><span>{item.open_brief_count} open brief{item.open_brief_count === 1 ? "" : "s"}</span>{item.entity_id && <Link href={`/entities/${item.entity_id}`}>View entity</Link>}</article>)}</section><section className="panel"><h2>My Focus Areas</h2>{state.data.focus.map((item) => <article className="watch-item" key={item.id}><div><small>{item.focus_type.replaceAll("_", " ")}</small><strong>{item.label}</strong><span>{item.recent_activity_count == null ? "Monitoring setup in progress" : `${item.recent_activity_count} signal${item.recent_activity_count === 1 ? "" : "s"} · 30 days`}</span></div>{item.entity_id && <Link href={`/entities/${item.entity_id}`}>View entity</Link>}</article>)}</section></div></section></WorkspaceShell>;
  }

  return <WorkspaceShell><section className="content-page"><div className="page-heading"><div><p className="eyebrow">Monitoring scope</p><h1>Watchlist & Focus Areas</h1></div><Link className="secondary-button" href="/onboarding/lens">Add a Focus Area</Link></div>
    {state.status === "loading" && <ModuleLoading label="Loading watchlist and Focus Areas" />}{state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
    {state.status === "ready" && <section className="panel watchlist-tabs"><div aria-label="Watchlist category" className="tab-strip" role="tablist">{tabs.map((value) => <button aria-selected={tab === value} className={tab === value ? "active" : ""} key={value} onClick={() => setTab(value)} role="tab" type="button">{value === "FOCUS" ? "My Focus Areas" : `${value[0]}${value.slice(1).toLowerCase()}s`}</button>)}</div><div className="watchlist-rows">{items.map((raw) => { const isFocus = "label" in raw; const title = isFocus ? raw.label : raw.name; const type = isFocus ? "FOCUS AREA" : raw.object_type; return <article className="watch-item-v2" key={raw.id}><div><small>{type.replaceAll("_", " ")}</small><h2>{title}</h2><p>{raw.recent_activity_count == null ? "Monitoring will begin when this context is matched" : `${raw.recent_activity_count} recent development${raw.recent_activity_count === 1 ? "" : "s"}`}{raw.open_brief_count ? ` · ${raw.open_brief_count} requiring attention` : ""}</p></div>{raw.entity_id ? <Link href={`/entities/${raw.entity_id}`} onClick={() => void recordProductEvent("WATCHLIST_ITEM_VIEWED", { object_type: type, object_id: raw.id })}>View</Link> : isFocus ? <Link href="/settings">Edit</Link> : <span>Monitoring</span>}</article>; })}{!items.length && <div className="quiet-state"><p>{tab === "FOCUS" ? stateMessages.focusEmpty : stateMessages.watchlistEmpty}</p></div>}</div></section>}
  </section></WorkspaceShell>;
}
