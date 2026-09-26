"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { generateDossier, getDossier, getDossiers, type Dossier } from "@/lib/competitors";
import { Citations } from "./evidence";
import { WinLossPanel } from "./win-loss-panel";

export function DossierExplorer() {
  const [items, setItems] = useState<Dossier[]>([]);
  const [selected, setSelected] = useState("");
  const [loadedDossier, setDossier] = useState<Dossier | null>(null);
  const dossier = loadedDossier?.id === selected ? loadedDossier : null;
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => { const value = await getDossiers(); setItems(value.items); setSelected(previous => previous || value.items[0]?.id || ""); }, []);
  useEffect(() => {
    let active = true;
    void getDossiers().then(value => { if (active) { setItems(value.items); setSelected(previous => previous || value.items[0]?.id || ""); } }).catch(err => { if (active) setError(err.message); });
    const update = () => void load().catch(err => setError(err.message));
    window.addEventListener("competitive-intelligence-updated", update);
    return () => { active = false; window.removeEventListener("competitive-intelligence-updated", update); };
  }, [load]);
  const pending = dossier?.processing_status === "queued" || dossier?.processing_status === "processing";
  useEffect(() => {
    if (!selected) return;
    let active = true;
    void getDossier(selected).then(value => { if (active) setDossier(value); }).catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [selected]);
  useEffect(() => {
    if (!selected || !pending) return;
    let active = true;
    const timer = setInterval(() => void getDossier(selected).then(value => { if (active) setDossier(value); }).catch(err => { if (active) setError(err.message); }), 4000);
    return () => { active = false; clearInterval(timer); };
  }, [selected, pending]);
  async function generate(value: string, refresh = false) {
    setBusy(true); setError("");
    try { const item = await generateDossier(value, refresh); await load(); setSelected(item.id); setDossier(await getDossier(item.id)); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not request dossier"); }
    finally { setBusy(false); }
  }
  return <div className="space-y-6">
    <section aria-label="Competitor dossier explorer" className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-200 p-5"><p className="text-xs font-semibold uppercase tracking-widest text-blue-700">Active competitive intelligence</p><h2 className="mt-1 text-2xl font-bold">Competitor dossiers</h2><p className="mt-2 text-sm text-slate-600">Research licenses, clearing rails, pricing and merchant fit. Compare public evidence with your operating footprint and field reports.</p>
        <form className="mt-4 flex gap-3" onSubmit={event => { event.preventDefault(); void generate(name.trim()); }}><input aria-label="Competitor to research" required minLength={2} maxLength={150} value={name} onChange={event => setName(event.target.value)} placeholder="Enter a fintech, bank or PSP" className="min-w-0 flex-1 rounded-lg border border-slate-300 p-3 text-sm" /><button disabled={busy || name.trim().length < 2} className="rounded-lg bg-slate-900 px-4 text-sm font-semibold text-white disabled:opacity-40">{busy ? "Requesting…" : "Generate dossier"}</button></form>
      </header>
      {error && <p role="alert" className="m-5 rounded bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      <div className="grid md:grid-cols-[220px_1fr]"><nav aria-label="Competitor dossiers" className="space-y-2 border-b border-slate-200 bg-slate-50 p-3 md:border-b-0 md:border-r">{items.map(item => <button key={item.id} onClick={() => setSelected(item.id)} aria-current={selected === item.id ? "true" : undefined} className={`w-full rounded-lg border p-3 text-left text-sm font-semibold ${selected === item.id ? "border-blue-500 bg-white text-blue-800" : "border-transparent text-slate-700"}`}>{item.competitor_name}</button>)}{!items.length && <p className="p-3 text-xs text-slate-500">Your researched competitors will appear here.</p>}</nav>
        <div className="min-w-0 space-y-5 p-5">{!dossier ? <p className="py-8 text-center text-sm text-slate-500">{selected ? "Loading dossier…" : "Enter a competitor name to start an evidence-backed profile."}</p> : <>
          <div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="text-xl font-bold">{dossier.competitor_name}</h3><p className="mt-1 text-xs text-slate-500">{dossier.last_refreshed_at ? `Last researched ${new Date(dossier.last_refreshed_at).toLocaleString()}` : "Not researched yet"}{dossier.canonical_domain && ` · ${dossier.canonical_domain}`}</p></div><button disabled={busy || pending} onClick={() => void generate(dossier.competitor_name, true)} className="rounded-lg border px-3 py-2 text-xs font-semibold disabled:opacity-40">Refresh research</button></div>
          {pending && <p role="status" className="rounded bg-blue-50 p-3 text-sm text-blue-900">Research queued or running. Gathering public evidence and comparing your footprint…{dossier.last_refreshed_at && " The previous profile remains visible until the refresh completes."}</p>}
          {dossier.processing_status === "failed" && <p role="status" className="rounded bg-amber-50 p-3 text-sm text-amber-900">{dossier.error_code === "NOT_RESEARCHED" ? "Field reports are linked to this competitor. Request research to build its dossier." : "Research could not be completed. Try refreshing; any previous profile is retained."}</p>}
          {dossier.last_refreshed_at && <>
            {dossier.provenance.live_search_available === false && <p className="text-xs text-amber-900">Live web evidence was unavailable. This profile uses previously collected signals.</p>}
            <div className="grid gap-4 sm:grid-cols-2">{[["Licensing evidence", dossier.profile.known_licenses], ["Clearing & settlement rails", dossier.profile.primary_settlement_rails], ["Target merchant segments", dossier.profile.core_target_segments]].map(([label, raw]) => { const claims = raw as typeof dossier.profile.known_licenses; return <article key={String(label)} className="rounded-lg bg-slate-50 p-4"><h4 className="text-xs font-bold uppercase text-slate-500">{String(label)}</h4>{claims?.length ? claims.map((claim, index) => <div key={index} className="mt-3 text-sm"><p>{claim.value}</p><Citations citations={claim.citations} sources={dossier.evidence} /></div>) : <p className="mt-3 text-sm text-slate-500">Not established by available evidence.</p>}</article>; })}<article className="rounded-lg bg-slate-50 p-4"><h4 className="text-xs font-bold uppercase text-slate-500">Fee structure</h4><p className="mt-3 text-sm">{dossier.fee_model_summary || "Not established by available evidence."}</p>{dossier.profile.fee_model && <Citations citations={dossier.profile.fee_model.citations} sources={dossier.evidence} />}</article></div>
            <div className="grid gap-4 lg:grid-cols-2">{[{title: "Where we can win", items: dossier.weaknesses_vs_us, style: "border-emerald-200 bg-emerald-50/40"}, {title: "Where we are vulnerable", items: dossier.strengths_vs_us, style: "border-amber-200 bg-amber-50/40"}].map(group => <section key={group.title} className={`rounded-xl border p-4 ${group.style}`}><h4 className="text-sm font-bold">{group.title}</h4><p className="mt-1 text-xs text-slate-500">Evidence-based comparisons to validate with buyers</p>{group.items.map((item, index) => <article key={index} className="mt-4 text-sm"><p className="font-semibold">{item.point}</p><p className="mt-1">{item.detail}</p><Citations citations={item.citations} sources={dossier.evidence} /></article>)}{!group.items.length && <p className="mt-3 text-sm text-slate-500">Insufficient evidence for a supported comparison.</p>}</section>)}</div>
            {!!dossier.profile.unknowns?.length && <div className="rounded-lg border border-dashed p-4"><h4 className="text-sm font-semibold">Questions still open</h4><ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-600">{dossier.profile.unknowns.map(item => <li key={item}>{item}</li>)}</ul></div>}
          </>}
          {!!dossier.battlecards?.length && <div><h4 className="text-sm font-bold">Active battlecards</h4>{dossier.battlecards.map(item => <Link className="mt-2 block text-sm text-blue-700 underline" key={item.id} href={`/workspace?artifact_id=${item.id}`}>{item.title}</Link>)}</div>}
        </>}</div>
      </div>
    </section>
    <WinLossPanel key={dossier?.competitor_name || "all"} competitor={dossier?.competitor_name || ""} />
  </div>;
}
