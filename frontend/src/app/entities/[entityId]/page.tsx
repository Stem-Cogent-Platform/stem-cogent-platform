"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CILPanel } from "@/components/cil-panel";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type EntityProfile = {
  entity: { id: string; canonical_name: string; entity_type: string; aliases: string[]; region_tags: string[] };
  activity: { id: string; title: string; source_url?: string; primary_domain?: string; published_at?: string }[];
  relationships: { relationship_type: string; related_entity_id: string; related_entity_name: string; confidence_score?: number; evidence_available: boolean }[];
};

export default function EntityPage() {
  const id = String(useParams<{ entityId: string }>().entityId ?? "");
  const [state, setState] = useState<LoadState<EntityProfile>>({ status: "loading" });
  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      setState({ status: "ready", data: await apiRequest<EntityProfile>(`/api/v1/entities/${id}`) });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Entity intelligence could not be loaded." });
    }
  }, [id]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  return (
    <WorkspaceShell>
      <section className="content-page">
        {state.status === "loading" && <ModuleLoading label="Loading entity intelligence" />}
        {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
        {state.status === "ready" && (
          <>
            <div className="page-heading"><div><p className="eyebrow">{state.data.entity.entity_type}</p><h1>{state.data.entity.canonical_name}</h1><p>{state.data.entity.region_tags.join(" · ")}</p></div></div>
            <div className="detail-grid">
              <article className="brief-detail">
                <h2>Recent verified activity</h2>
                {state.data.activity.length ? (
                  <ul className="evidence-list">
                    {state.data.activity.map((item) => <li key={item.id}><div><strong>{item.title}</strong><small>{item.primary_domain?.replaceAll("_", " ")}</small></div>{item.source_url && <a href={item.source_url} rel="noreferrer" target="_blank">Open source</a>}</li>)}
                  </ul>
                ) : <p>No verified recent activity is available for this entity yet.</p>}
                <h2>Known relationships</h2>
                {state.data.relationships.length ? (
                  <ul>{state.data.relationships.map((item) => <li key={`${item.relationship_type}-${item.related_entity_id}`}>{item.relationship_type.replaceAll("_", " ")} — {item.related_entity_name}</li>)}</ul>
                ) : <p>No verified relationships are available for this entity yet.</p>}
              </article>
              <CILPanel anchorId={id} anchorType="ENTITY" hasRelationships={state.data.relationships.some((item) => item.evidence_available)} />
            </div>
          </>
        )}
      </section>
    </WorkspaceShell>
  );
}
