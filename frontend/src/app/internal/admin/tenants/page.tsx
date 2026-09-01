"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { InternalAdminShell } from "@/components/internal-admin-shell";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type Tenant = { id: string; name: string; status: string; pilot_status: string; started_at?: string; ends_at?: string; pilot_owner?: string; pending_invites: number };

export default function AdminTenantsPage() {
  const [state, setState] = useState<LoadState<Tenant[]>>({ status: "loading" });
  const [name, setName] = useState("");
  const [owner, setOwner] = useState("");
  const [saving, setSaving] = useState(false);
  const load = useCallback(async () => { try { setState({ status: "ready", data: await apiRequest<Tenant[]>("/api/v1/internal/admin/tenants") }); } catch { setState({ status: "error", message: "Pilot tenants could not be loaded." }); } }, []);
  useEffect(() => { const timer = setTimeout(() => void load(), 0); return () => clearTimeout(timer); }, [load]);
  async function create(event: FormEvent) { event.preventDefault(); setSaving(true); try { await apiRequest("/api/v1/internal/admin/tenants", { method: "POST", body: JSON.stringify({ canonical_company_name: name, pilot_owner: owner || undefined }) }); setName(""); setOwner(""); await load(); } finally { setSaving(false); } }
  return <InternalAdminShell><header className="internal-heading"><div><p className="eyebrow">Guided pilot operations</p><h1>Pilot tenants</h1></div><span>{state.status === "ready" ? state.data.length : "–"} engagements</span></header><section className="internal-card"><h2>Provision tenant</h2><form className="inline-admin-form" onSubmit={create}><label><span>Canonical company name</span><input onChange={(event) => setName(event.target.value)} required value={name} /></label><label><span>Pilot owner</span><input onChange={(event) => setOwner(event.target.value)} value={owner} /></label><button className="primary-button" disabled={saving} type="submit">{saving ? "Creating..." : "Create tenant"}</button></form></section>{state.status === "loading" && <ModuleLoading />}{state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}{state.status === "ready" && <section className="internal-table" aria-label="Pilot tenants"><div className="internal-table-head"><span>Tenant</span><span>Pilot</span><span>Owner</span><span>Invites</span><span /></div>{state.data.map((tenant) => <article key={tenant.id}><div><strong>{tenant.name}</strong><small>{tenant.status}</small></div><span className={`admin-status status-${tenant.pilot_status?.toLowerCase()}`}>{tenant.pilot_status || "SETUP"}</span><span>{tenant.pilot_owner || "Unassigned"}</span><span>{tenant.pending_invites} pending</span><Link href={`/internal/admin/tenants/${tenant.id}`}>Open →</Link></article>)}</section>}</InternalAdminShell>;
}
