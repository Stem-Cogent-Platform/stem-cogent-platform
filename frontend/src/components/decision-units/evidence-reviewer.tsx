"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { downloadPolicy, getAuditHistory, getAudits, getPolicies, getRegulatorySignals, reviewAudit, startAudit, statusLabels } from "@/lib/compliance";
import type { AuditList, GapStatus, Policy, ReviewEvent } from "@/lib/compliance";

const badge: Record<string, string> = {
  adequately_met: "bg-emerald-50 text-emerald-800 border-emerald-200",
  partially_met: "bg-amber-50 text-amber-900 border-amber-200",
  gap_deficient: "bg-red-50 text-red-800 border-red-200",
};
const field = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm";
const button = "rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40";

export function EvidenceReviewer({ initialSignalId }: {initialSignalId?: string | null}) {
  const [signals, setSignals] = useState<Array<{id: string; title: string}>>([]);
  const [signal, setSignal] = useState(initialSignalId ?? "");
  const [data, setData] = useState<AuditList>({run: null, items: []});
  const [selected, setSelected] = useState("");
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [history, setHistory] = useState<ReviewEvent[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [reason, setReason] = useState("");
  const [overrideStatus, setOverrideStatus] = useState<GapStatus>("partially_met");
  const [policy, setPolicy] = useState("");
  const audit = data.items.find(item => item.id === selected) ?? data.items[0];
  const running = data.run?.processing_status === "queued" || data.run?.processing_status === "processing";
  const load = useCallback(async () => { if (signal) setData(await getAudits(signal)); }, [signal]);

  useEffect(() => {
    let active = true;
    void Promise.all([getRegulatorySignals(), getPolicies()]).then(([sources, documents]) => {
      if (!active) return;
      setSignals(sources.items); setPolicies(documents.items);
      setSignal(previous => previous || sources.items[0]?.id || "");
    }).catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, []);
  useEffect(() => { if (initialSignalId) setSignal(initialSignalId); }, [initialSignalId]);
  useEffect(() => {
    if (!signal) return;
    let active = true;
    setLoading(true); setData({run: null, items: []}); setSelected(""); setError("");
    void getAudits(signal).then(value => { if (active) setData(value); })
      .catch(err => { if (active) setError(err.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [signal]);
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => { void load().catch(err => setError(err.message)); }, 4000);
    return () => clearInterval(timer);
  }, [running, load]);
  useEffect(() => {
    setHistory([]); setReason("");
    if (!audit) return;
    let active = true;
    void getAuditHistory(audit.id).then(result => { if (active) setHistory(result.items); }).catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [audit?.id, audit?.revision, audit?.signed_off_at]);

  async function run() {
    setBusy(true); setError("");
    try { await startAudit(signal); await load(); } catch (err) { setError(err instanceof Error ? err.message : "Could not start audit"); }
    finally { setBusy(false); }
  }
  async function review(action: "override" | "addendum" | "sign-off") {
    if (!audit) return;
    setBusy(true); setError("");
    try {
      await reviewAudit(audit, action, reason.trim(), action === "override" ? overrideStatus : undefined, action === "addendum" ? policy : undefined);
      await load(); setHistory((await getAuditHistory(audit.id)).items); setReason("");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not save review"); }
    finally { setBusy(false); }
  }

  return <section className="rounded-2xl border border-slate-200 bg-white shadow-sm" aria-label="Regulatory evidence reviewer">
    <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 p-5">
      <div><p className="text-xs font-semibold uppercase tracking-widest text-blue-700">Evidence audit</p><h2 className="text-xl font-bold text-slate-900">Obligations register</h2><p className="mt-1 text-xs text-slate-500">Policy evidence coverage, with a separate human review trail.</p></div>
      <Link href="/settings/policies" className="text-sm font-semibold text-blue-700 underline">Open policy vault</Link>
    </div>
    <div className="flex flex-wrap items-end gap-3 p-5">
      <label className="min-w-0 flex-1 text-xs font-semibold text-slate-600">Regulatory circular<select className={field + " mt-1"} value={signal} onChange={event => setSignal(event.target.value)}><option value="">Select a circular</option>{signals.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
      <button className={button} disabled={!signal || busy || running} onClick={() => void run()}>{running ? "Assessment running…" : "Run evidence audit"}</button>
    </div>
    {error && <p role="alert" className="mx-5 mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
    {data.run && <p role="status" className="px-5 pb-4 text-xs text-slate-600">Latest run: <strong>{data.run.processing_status.replaceAll("_", " ")}</strong>{data.run.error_code && ` · ${data.run.error_code.replaceAll("_", " ")}`}{data.run.processing_status === "needs_source" && " — Full official circular text is required. A summary cannot establish clause-level obligations."}</p>}
    {loading ? <p className="p-5 text-sm" role="status">Loading evidence…</p> : !audit ? <div className="border-t border-slate-100 p-8 text-center text-sm text-slate-600">{running ? "The source and internal policies are being assessed. Results will appear here." : "No completed evidence assessment for this circular. Upload policies, then run an audit."}</div> :
      <div className="grid border-t border-slate-200 lg:grid-cols-[280px_1fr]">
        <nav className="max-h-[800px] space-y-2 overflow-y-auto border-b border-slate-200 bg-slate-50 p-3 lg:border-b-0 lg:border-r" aria-label="Extracted obligations">{data.items.map(item => <button type="button" key={item.id} onClick={() => setSelected(item.id)} aria-current={audit.id === item.id ? "true" : undefined} className={`w-full rounded-lg border p-3 text-left ${audit.id === item.id ? "border-blue-500 bg-white ring-1 ring-blue-500" : "border-slate-200 bg-white"}`}><span className="text-xs font-mono text-slate-500">{item.clause_reference}</span><span className="mt-1 block text-sm font-semibold text-slate-900">{item.requirement_title}</span><span className={`mt-2 inline-block rounded border px-2 py-1 text-[11px] font-semibold ${badge[item.status]}`}>{statusLabels[item.status]}</span></button>)}</nav>
        <div className="min-w-0 space-y-5 p-5">
          {audit.run_id !== data.run?.id && <p className="rounded bg-amber-50 p-3 text-sm text-amber-900">These are earlier results. The latest run has not completed.</p>}
          <header><p className="text-xs font-mono text-slate-500">Clause {audit.clause_reference}</p><h3 className="mt-1 text-lg font-bold">{audit.requirement_title}</h3><div className="mt-2 flex flex-wrap gap-3 text-xs"><span className={`rounded border px-2 py-1 ${badge[audit.status]}`}>{statusLabels[audit.status]}</span><span className="py-1">AI evidence score: {Number(audit.compliance_score).toFixed(0)}%</span><span className="py-1">Revision {audit.revision}</span>{audit.signed_off_at && <span className="py-1 text-emerald-800">Signed off {new Date(audit.signed_off_at).toLocaleDateString()}</span>}</div></header>
          {audit.reviewer_override && <p className="rounded-lg bg-blue-50 p-3 text-xs text-blue-900">Reviewer override: {audit.reviewer_override.reason} · Original AI status: {statusLabels[audit.automated_status]}</p>}
          <details className="rounded-lg border border-slate-200 p-3"><summary className="cursor-pointer text-sm font-semibold">Regulatory source evidence</summary><blockquote className="mt-3 whitespace-pre-wrap text-sm text-slate-700">{audit.source_excerpt}</blockquote><a className="mt-2 block text-xs text-blue-700 underline" href={audit.source_url} target="_blank" rel="noreferrer">Open official source</a>{audit.statutory_sanction && <p className="mt-2 text-xs">Stated sanction: {audit.statutory_sanction}</p>}{audit.statutory_deadline && <p className="text-xs">Stated deadline: {audit.statutory_deadline}</p>}</details>
          <div className="space-y-3">{audit.evidence_matches.map((criterion, index) => <article key={index} className="grid overflow-hidden rounded-lg border border-slate-200 md:grid-cols-2"><div className={`p-4 ${criterion.verdict === "satisfied" ? "bg-slate-50" : "bg-amber-50"}`}><p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Assessment criterion {index + 1}</p><p className="mt-2 text-sm font-semibold">{criterion.criterion}</p><p className={`mt-2 text-xs font-bold ${criterion.verdict === "satisfied" ? "text-emerald-800" : "text-red-800"}`}>{criterion.verdict.toUpperCase()}</p><p className="mt-2 text-xs text-slate-700">{criterion.reasoning}</p></div><div className="space-y-4 p-4">{criterion.evidence.length ? criterion.evidence.map(item => <div key={item.chunk_id}><button className="text-left text-xs font-semibold text-blue-700 underline" onClick={() => void downloadPolicy(item.policy_id).catch(err => setError(err.message))}>{item.matched_policy_title} · v{item.policy_version}</button><blockquote className="mt-2 whitespace-pre-wrap border-l-2 border-blue-200 pl-3 text-sm text-slate-700">{item.excerpt}</blockquote><p className="mt-2 text-[11px] text-slate-500">Similarity {(item.similarity_score * 100).toFixed(1)}% · {item.location.sources?.map(source => source.page ? `page ${source.page}` : source.table ? `table ${source.table}` : `paragraph ${source.paragraph}`).join(", ")}</p></div>) : <p className="text-sm font-semibold text-red-800">No verified policy evidence for this criterion.</p>}</div></article>)}</div>
          <fieldset disabled={busy || running || audit.run_id !== data.run?.id} className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4"><legend className="px-1 text-sm font-bold">Reviewer actions</legend><label className="block text-xs font-semibold">Justification or sign-off note<textarea className={field + " mt-1"} value={reason} onChange={event => setReason(event.target.value)} minLength={10} maxLength={4000} rows={3} placeholder="Explain the evidence supporting your decision (at least 10 characters)." /></label><div className="grid gap-3 sm:grid-cols-2"><label className="text-xs">Override status<select className={field + " mt-1"} value={overrideStatus} onChange={event => setOverrideStatus(event.target.value as GapStatus)}>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="text-xs">Supporting addendum<select className={field + " mt-1"} value={policy} onChange={event => setPolicy(event.target.value)}><option value="">Select a ready policy</option>{policies.filter(item => item.processing_status === "ready").map(item => <option key={item.id} value={item.id}>{item.document_title} v{item.version}</option>)}</select></label></div><div className="flex flex-wrap gap-2"><button className={button} disabled={reason.trim().length < 10} onClick={() => void review("override")}>Override status</button><button className={button} disabled={reason.trim().length < 10 || !policy} onClick={() => void review("addendum")}>Attach addendum</button><button className={button} disabled={reason.trim().length < 10} onClick={() => void review("sign-off")}>Log audit sign-off</button></div></fieldset>
          <details className="rounded-lg border border-slate-200 p-3"><summary className="cursor-pointer text-sm font-semibold">Immutable review history ({history.length})</summary><ol className="mt-3 space-y-3">{history.map(event => <li key={event.id} className="border-l-2 border-slate-200 pl-3 text-xs"><strong>{event.event_type.replaceAll("_", " ")} · revision {event.revision}</strong><p className="mt-1">{event.reason}</p><time className="text-slate-500">{new Date(event.created_at).toLocaleString()}</time></li>)}</ol></details>
        </div>
      </div>}
  </section>;
}
