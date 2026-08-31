"use client";

import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { InternalAdminShell } from "@/components/internal-admin-shell";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type Row = Record<string, string | number | boolean | null>;
type Detail = { tenant: Row; checklist: Record<string, boolean>; company_objects: Row[]; users: Row[]; invitations: Row[]; activations: Row[]; briefs: Row[] };
type Metrics = Row;
const tabs = ["Overview", "Company Context", "Entity Resolution", "Activation", "Users & Invites", "Decision Briefs", "Usage", "Internal Notes"] as const;

function DataRows({ rows, empty }: { rows: Row[]; empty: string }) {
  if (!rows.length) return <p className="quiet-state">{empty}</p>;
  return <div className="admin-data-rows">{rows.map((row, index) => <article key={String(row.id ?? index)}>{Object.entries(row).filter(([, value]) => value !== null).slice(0, 6).map(([key, value]) => <div key={key}><small>{key.replaceAll("_", " ")}</small><span>{String(value)}</span></div>)}</article>)}</div>;
}

export default function TenantDetailPage() {
  const id = String(useParams<{ tenantId: string }>().tenantId);
  const [state, setState] = useState<LoadState<{ detail: Detail; metrics: Metrics }>>({ status: "loading" });
  const [tab, setTab] = useState<(typeof tabs)[number]>("Overview");
  const [email, setEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState("");
  const load = useCallback(async () => { try { const [detail, metrics] = await Promise.all([apiRequest<Detail>(`/api/v1/internal/admin/tenants/${id}`), apiRequest<Metrics>(`/api/v1/internal/admin/tenants/${id}/metrics`)]); setState({ status: "ready", data: { detail, metrics } }); setNotes(String(detail.tenant.internal_notes ?? "")); } catch { setState({ status: "error", message: "Pilot tenant could not be loaded." }); } }, [id]);
  useEffect(() => { const timer = setTimeout(() => void load(), 0); return () => clearTimeout(timer); }, [load]);
  async function operation(name: string, path: string, init?: RequestInit) { setPending(name); setMessage(""); try { const result = await apiRequest<Record<string, unknown>>(path, init); setMessage(name === "Invite" && result.invitation_url ? `Single-use invitation: ${result.invitation_url}` : `${name} completed.`); await load(); } catch { setMessage(`${name} could not be completed.`); } finally { setPending(""); } }
  async function invite(event: FormEvent) { event.preventDefault(); await operation("Invite", `/api/v1/internal/admin/tenants/${id}/invitations`, { method: "POST", body: JSON.stringify({ email }) }); setEmail(""); }
  if (state.status === "loading") return <InternalAdminShell><ModuleLoading /></InternalAdminShell>;
  if (state.status === "error") return <InternalAdminShell><ModuleFailure message={state.message} retry={() => void load()} /></InternalAdminShell>;
  const { detail, metrics } = state.data;
  return <InternalAdminShell><header className="internal-heading"><div><p className="eyebrow">Pilot tenant</p><h1>{String(detail.tenant.name)}</h1></div><span className="admin-status">{String(detail.tenant.status)}</span></header><div className="admin-tabs" role="tablist">{tabs.map((item) => <button aria-selected={tab === item} className={tab === item ? "active" : ""} key={item} onClick={() => setTab(item)} role="tab" type="button">{item}</button>)}</div>{message && <p className="form-message" role="status">{message}</p>}<section className="internal-card tenant-tab">
    {tab === "Overview" && <><h2>Readiness checklist</h2><div className="readiness-grid">{Object.entries(detail.checklist).map(([key, ready]) => <div className={ready ? "ready" : "pending"} key={key}><span>{ready ? "✓" : "○"}</span>{key.replaceAll("_", " ")}</div>)}</div></>}
    {tab === "Company Context" && <><h2>Company Context</h2><div className="semantic-chips">{[...(detail.tenant.business_categories as unknown as string[] ?? []), ...(detail.tenant.operating_markets as unknown as string[] ?? []), ...(detail.tenant.strategic_priorities as unknown as string[] ?? [])].map((value) => <span key={value}>{value}</span>)}</div><DataRows empty="No Company Context objects are configured." rows={detail.company_objects} /></>}
    {tab === "Entity Resolution" && <><div className="internal-section-heading"><h2>Resolution outcomes</h2><button className="secondary-button" disabled={pending !== ""} onClick={() => void operation("Entity audit", `/api/v1/internal/admin/tenants/${id}/entity-resolution`, { method: "POST" })} type="button">Run deterministic audit</button></div><DataRows empty="No context objects are available." rows={detail.company_objects} /></>}
    {tab === "Activation" && <><div className="internal-section-heading"><h2>Historical activation</h2><button className="primary-button" disabled={pending !== ""} onClick={() => void operation("Activation", `/api/v1/internal/admin/tenants/${id}/activation`, { method: "POST", body: JSON.stringify({ lookback_days: 45 }) })} type="button">Start activation</button></div><DataRows empty="No activation has run." rows={detail.activations} /></>}
    {tab === "Users & Invites" && <><h2>Users & invitations</h2><form className="inline-admin-form" onSubmit={invite}><label><span>Invite email</span><input onChange={(event) => setEmail(event.target.value)} required type="email" value={email} /></label><button className="primary-button" disabled={pending !== ""} type="submit">Create 48-hour invite</button></form><DataRows empty="No users have accepted an invitation." rows={detail.users} /><DataRows empty="No invitations have been issued." rows={detail.invitations} /></>}
    {tab === "Decision Briefs" && <><h2>Decision Briefs</h2><DataRows empty="No briefs have been created." rows={detail.briefs} /></>}
    {tab === "Usage" && <><h2>Pilot learning metrics</h2><div className="admin-metric-grid usage-grid">{Object.entries(metrics).filter(([key]) => !["started_at", "ends_at", "first_useful_brief_available_at"].includes(key)).map(([key, value]) => <article key={key}><span>{key.replaceAll("_", " ")}</span><strong>{value === null ? "–" : typeof value === "number" && key.includes("rate") ? `${Math.round(value * 100)}%` : String(value)}</strong></article>)}</div></>}
    {tab === "Internal Notes" && <><h2>Internal notes</h2><label className="admin-notes"><span>Visible only to Stem operators</span><textarea onChange={(event) => setNotes(event.target.value)} rows={10} value={notes} /></label><button className="primary-button" disabled={pending !== ""} onClick={() => void operation("Notes", `/api/v1/internal/admin/tenants/${id}`, { method: "PATCH", body: JSON.stringify({ internal_notes: notes }) })} type="button">Save notes</button></>}
  </section></InternalAdminShell>;
}
