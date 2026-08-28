"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type SearchItem = { id: string; title: string; summary?: string; domain?: string; urgency?: string };
type SearchResults = { briefs: SearchItem[]; intelligence: SearchItem[]; entities: SearchItem[] };

function Results() {
  const params = useSearchParams();
  const query = params.get("q")?.trim() ?? "";
  const [state, setState] = useState<LoadState<SearchResults>>({ status: "loading" });
  const load = useCallback(async () => {
    if (query.length < 2) {
      setState({ status: "ready", data: { briefs: [], intelligence: [], entities: [] } });
      return;
    }
    try {
      setState({ status: "ready", data: await apiRequest<SearchResults>(`/api/v1/search?q=${encodeURIComponent(query)}`) });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Search could not be completed." });
    }
  }, [query]);
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  if (state.status === "loading") return <ModuleLoading />;
  if (state.status === "error") return <ModuleFailure message={state.message} retry={() => void load()} />;
  const groups = [
    ["Decision Briefs", state.data.briefs, "/briefs/"],
    ["Wider Intelligence", state.data.intelligence, "/intelligence?item="],
    ["Entities", state.data.entities, "/entities/"]
  ] as const;
  const count = state.data.briefs.length + state.data.intelligence.length + state.data.entities.length;
  if (!count) return <section className="empty-brief"><h2>No results for “{query}”</h2><p>Try an entity, policy, market, company, or regulatory term.</p></section>;
  return <div className="search-results">{groups.map(([title, items, href]) => items.length > 0 && <section key={title}><h2>{title}</h2>{items.map((item) => <Link className="search-result" href={`${href}${item.id}`} key={item.id}><div><strong>{item.title}</strong><p>{item.summary?.replaceAll("_", " ")}</p></div><span>{item.domain?.replaceAll("_", " ") ?? "View"} →</span></Link>)}</section>)}</div>;
}

export default function SearchPage() {
  return <WorkspaceShell><section className="content-page"><div className="page-heading"><div><p className="eyebrow">Workspace search</p><h1>Search results</h1><p>Decision-relevant results from your permitted workspace data and verified intelligence.</p></div></div><Suspense fallback={<ModuleLoading />}><Results /></Suspense></section></WorkspaceShell>;
}
