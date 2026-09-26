"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { getDeal, getInsights, retryDeal, type DealSignal, type Insights } from "@/lib/competitors";

export function WinLossPanel({competitor = ""}: {competitor?: string}) {
  const [data, setData] = useState<Insights | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [segment, setSegment] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");
  const [detail, setDetail] = useState<DealSignal | null>(null);
  const load = useCallback(async () => { const result = await getInsights({...filters, competitor_name: competitor}); setData(result); }, [competitor, filters]);
  useEffect(() => {
    let active = true;
    void getInsights({...filters, competitor_name: competitor}).then(value => { if (active) setData(value); }).catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [competitor, filters]);
  useEffect(() => { const update = () => { void load().catch(err => setError(err.message)); }; window.addEventListener("competitive-intelligence-updated", update); return () => window.removeEventListener("competitive-intelligence-updated", update); }, [load]);
  useEffect(() => { if (!data?.metrics.pending) return; const timer = setInterval(() => void load().catch(err => setError(err.message)), 4000); return () => clearInterval(timer); }, [data?.metrics.pending, load]);
  async function copy(item: DealSignal) { try { await navigator.clipboard.writeText(item.winning_talk_track || ""); setCopied(item.id); } catch { setError("Clipboard is unavailable. Select and copy the talk track text."); } }
  return <section aria-label="Win and loss insights" className="space-y-5 rounded-2xl border border-slate-200 bg-white p-5">
    <header className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-blue-700">Field intelligence</p><h2 className="mt-1 text-xl font-bold">Win / loss insights</h2><p className="mt-1 text-xs text-slate-500">{competitor || "All competitors"} · Reported merchant decisions and objections</p></div><Link className="text-sm font-semibold text-blue-700 underline" href={`/workspace?mode=competitive&query=${encodeURIComponent(`Why do we lose deals${competitor ? ` against ${competitor}` : ""}?`)}`}>Investigate with Copilot</Link></header>
    <form className="flex flex-wrap items-end gap-3" onSubmit={event => { event.preventDefault(); setData(null); setError(""); setDetail(null); setFilters({start_date: start, end_date: end, merchant_segment: segment.trim()}); }}>
      <label className="text-xs">From<input type="date" value={start} onChange={event => setStart(event.target.value)} className="mt-1 block rounded border p-2" /></label>
      <label className="text-xs">Through<input type="date" value={end} min={start || undefined} onChange={event => setEnd(event.target.value)} className="mt-1 block rounded border p-2" /></label>
      <label className="text-xs">Segment<input value={segment} onChange={event => setSegment(event.target.value)} placeholder="All segments" className="mt-1 block rounded border p-2" /></label><button className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white">Apply filters</button>
    </form>
    {error && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-800">{error}</p>}
    {!data && !error && <p role="status" className="text-sm text-slate-500">Loading field intelligence…</p>}
    {data && <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{[["Won", data.metrics.won], ["Lost", data.metrics.lost], ["Churned", data.metrics.churned], ["Win rate", data.metrics.win_rate === null ? "Not established" : `${data.metrics.win_rate}%`]].map(([label, value]) => <div key={label} className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p></div>)}</div>
      <p className="text-xs text-slate-500">{data.metric_definition} {data.metrics.pending > 0 && `${data.metrics.pending} reports are being processed.`} {data.metrics.failed > 0 && `${data.metrics.failed} reports need extraction retry.`}</p>
      {data.metrics.reported === 0 && <p className="rounded-lg border border-dashed p-6 text-center text-sm text-slate-500">No field reports in this scope. Use “Log deal signal” to record a merchant decision.</p>}
      {data.themes.length > 0 && <div><h3 className="mb-3 text-sm font-bold">Decision drivers by outcome</h3><div className="flex flex-wrap gap-2">{data.themes.map(item => <span key={`${item.theme}-${item.deal_outcome}`} className="rounded-lg border border-slate-200 px-3 py-2 text-xs"><strong className="capitalize">{item.theme}</strong> · {item.deal_outcome}: {item.count}</span>)}</div></div>}
      <div className="grid gap-5 lg:grid-cols-2"><div><h3 className="mb-3 text-sm font-bold">Win stories & reported talk tracks</h3><div className="space-y-3">{data.recent_signals.filter(item => item.deal_outcome === "won" && item.processing_status === "ready").map(item => <article key={item.id} className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-4"><h4 className="text-sm font-semibold">Won {item.deal_size_arr_or_gmv || "a merchant"} against {item.competitor_name_raw}</h4><p className="mt-1 text-xs text-slate-500">{item.merchant_segment} · {item.occurred_on} · Field report</p><p className="mt-3 text-sm">{item.extracted_decision_drivers.join(" · ") || "No explicit driver recorded"}</p>{item.winning_talk_track && <><p className="mt-3 text-xs font-semibold">{item.talk_track_kind === "observed" ? "Reported pitch" : "Suggested pitch — untested"}</p><blockquote className="mt-1 text-sm">{item.winning_talk_track}</blockquote><button className="mt-2 text-xs text-blue-700 underline" onClick={() => void copy(item)}>{copied === item.id ? "Copied" : "Copy talk track"}</button></>}<button className="ml-3 mt-2 text-xs text-blue-700 underline" onClick={() => void getDeal(item.id).then(setDetail).catch(err => setError(err.message))}>Inspect field evidence</button></article>)}</div></div>
        <div><h3 className="mb-3 text-sm font-bold">Objection library</h3><div className="space-y-3">{data.objections.map(item => <article key={item.objection} className="rounded-xl border border-slate-200 p-4"><p className="text-sm font-semibold">{item.objection}</p><p className="mt-1 text-xs text-slate-500">{item.count} field reports</p><div className="mt-2 flex flex-wrap gap-3">{item.source_ids.map((id, index) => <button key={id} className="text-xs text-blue-700 underline" onClick={() => void getDeal(id).then(setDetail).catch(err => setError(err.message))}>Evidence {index + 1}</button>)}</div></article>)}</div></div></div>
      {detail && <section className="rounded-xl border border-blue-200 bg-blue-50 p-4" aria-label="Field report evidence"><div className="flex justify-between gap-4"><h3 className="text-sm font-bold">{detail.competitor_name_raw} · {detail.deal_outcome} · {detail.occurred_on}</h3><button className="text-xs underline" onClick={() => setDetail(null)}>Close evidence</button></div><blockquote className="mt-3 whitespace-pre-wrap text-sm">{detail.raw_sales_notes}</blockquote></section>}
      <details className="text-xs"><summary className="cursor-pointer font-semibold">Recent field reports ({data.recent_signals.length})</summary><ul className="mt-3 space-y-2">{data.recent_signals.map(item => <li key={item.id} className="flex flex-wrap justify-between gap-2 rounded border p-3"><button className="text-left text-blue-700 underline" onClick={() => void getDeal(item.id).then(setDetail).catch(err => setError(err.message))}>{item.competitor_name_raw} · {item.deal_outcome} · {item.merchant_segment} · {item.occurred_on}</button><span>{item.processing_status}</span>{item.processing_status === "failed" && <button className="underline" onClick={() => void retryDeal(item.id).then(load).catch(err => setError(err.message))}>Retry extraction</button>}</li>)}</ul></details>
    </>}
  </section>;
}
