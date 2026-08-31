"use client";

import { useCallback, useEffect, useState } from "react";
import { InternalAdminShell } from "@/components/internal-admin-shell";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type Review = { id: string; tenant_id: string; tenant_name: string; name: string; object_type: string; resolution_status: string };
export default function EntityReviewPage() {
  const [state, setState] = useState<LoadState<Review[]>>({ status: "loading" });
  const [pending, setPending] = useState("");
  const load = useCallback(async () => { try { setState({ status: "ready", data: await apiRequest<Review[]>("/api/v1/internal/admin/entity-review") }); } catch { setState({ status: "error", message: "Entity review queue could not be loaded." }); } }, []);
  useEffect(() => { const timer = setTimeout(() => void load(), 0); return () => clearTimeout(timer); }, [load]);
  async function dismiss(id: string) { setPending(id); try { await apiRequest(`/api/v1/internal/admin/entity-review/${id}`, { method: "POST", body: JSON.stringify({ action: "DISMISS" }) }); await load(); } finally { setPending(""); } }
  return <InternalAdminShell><header className="internal-heading"><div><p className="eyebrow">Company Context quality</p><h1>Entity review</h1></div><span>{state.status === "ready" ? state.data.length : "–"} unresolved</span></header>{state.status === "loading" && <ModuleLoading />}{state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}{state.status === "ready" && <section className="internal-table entity-review-table"><div className="internal-table-head"><span>Context value</span><span>Tenant</span><span>Type</span><span>Status</span><span /></div>{state.data.map((item) => <article key={item.id}><div><strong>{item.name}</strong><small>{item.id}</small></div><span>{item.tenant_name}</span><span>{item.object_type}</span><span className="admin-status">{item.resolution_status}</span><button disabled={pending === item.id} onClick={() => void dismiss(item.id)} type="button">{pending === item.id ? "Saving..." : "Not applicable"}</button></article>)}{!state.data.length && <p className="quiet-state">Every active Company Context value has a resolution outcome.</p>}</section>}</InternalAdminShell>;
}
