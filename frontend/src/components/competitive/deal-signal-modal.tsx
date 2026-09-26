"use client";

import { useEffect, useRef, useState } from "react";
import { apiRequest } from "@/lib/api";
import { getDeal, getDossiers, retryDeal, type DealSignal } from "@/lib/competitors";

const field = "mt-1 w-full rounded-lg border border-slate-300 bg-white p-2 text-sm";

export function DealSignalIntake() {
  const [open, setOpen] = useState(false);
  return <><button type="button" className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-800" onClick={() => setOpen(true)}>Log deal signal</button>{open && <DealSignalModal onClose={() => setOpen(false)} />}</>;
}

function DealSignalModal({onClose}: {onClose: () => void}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const request = useRef<{body: string; key: string} | null>(null);
  const [competitors, setCompetitors] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [outcome, setOutcome] = useState("won");
  const [segment, setSegment] = useState("");
  const [amount, setAmount] = useState("");
  const [occurred, setOccurred] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<DealSignal | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { dialog.current?.showModal(); let active = true; void getDossiers().then(value => { if (active) setCompetitors(value.items.map(item => item.competitor_name)); }).catch(() => {}); return () => { active = false; }; }, []);
  const pending = result?.processing_status === "queued" || result?.processing_status === "processing";
  const resultId = result?.id;
  useEffect(() => {
    if (!pending || !resultId) return;
    let active = true;
    const timer = setInterval(() => { void getDeal(resultId).then(value => { if (active) { setResult(value); if (value.processing_status === "ready") window.dispatchEvent(new Event("competitive-intelligence-updated")); } }).catch(err => { if (active) setError(err.message); }); }, 3000);
    return () => { active = false; clearInterval(timer); };
  }, [pending, resultId]);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    const values = {competitor_name: name.trim(), deal_outcome: outcome, merchant_segment: segment.trim(), deal_size_arr_or_gmv: amount.trim() || null, raw_sales_notes: notes.trim(), occurred_on: occurred};
    const body = JSON.stringify(values);
    if (request.current?.body !== body) request.current = {body, key: crypto.randomUUID()};
    try { setResult(await apiRequest<DealSignal>("/api/v1/competitors/deal-signals", {method: "POST", body: JSON.stringify({...values, idempotency_key: request.current.key})})); window.dispatchEvent(new Event("competitive-intelligence-updated")); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not save field report"); }
    finally { setBusy(false); }
  }
  return <dialog ref={dialog} onCancel={onClose} aria-labelledby="deal-intake-title" className="max-h-[90vh] w-[min(95vw,640px)] overflow-y-auto rounded-2xl p-6 shadow-xl backdrop:bg-slate-950/50">
    <div className="flex items-start justify-between gap-4"><div><h2 id="deal-intake-title" className="text-xl font-bold">Log deal signal</h2><p className="mt-1 text-xs text-slate-500">Capture a merchant conversation, objection or deal outcome.</p></div><button type="button" onClick={onClose} aria-label="Close deal signal" className="rounded border px-3 py-1">Close</button></div>
    {error && <p role="alert" className="mt-4 rounded bg-red-50 p-3 text-sm text-red-800">{error}</p>}
    {!result ? <form className="mt-5 space-y-4" onSubmit={event => void submit(event)}>
      <label className="block text-xs font-semibold">Competitor<input autoFocus list="deal-competitors" className={field} required minLength={2} maxLength={150} value={name} onChange={event => setName(event.target.value)} placeholder="Company name" /></label><datalist id="deal-competitors">{competitors.map(value => <option key={value} value={value} />)}</datalist>
      <fieldset><legend className="mb-2 text-xs font-semibold">Outcome</legend><div className="flex gap-2">{[["won", "Deal won"], ["lost", "Deal lost"], ["churned", "Customer churned"]].map(([value, label]) => <label key={value} className={`rounded-lg border px-3 py-2 text-xs ${outcome === value ? "border-blue-500 bg-blue-50" : "border-slate-200"}`}><input type="radio" name="deal-outcome" value={value} checked={outcome === value} onChange={() => setOutcome(value)} className="mr-2" />{label}</label>)}</div></fieldset>
      <div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-semibold">Merchant segment<input className={field} required minLength={2} maxLength={100} value={segment} onChange={event => setSegment(event.target.value)} placeholder="Retail checkout" /></label><label className="text-xs font-semibold">Estimated deal size or GMV<input className={field} maxLength={100} value={amount} onChange={event => setAmount(event.target.value)} placeholder="NGN 40M monthly GMV (optional)" /></label></div>
      <label className="block text-xs font-semibold">Deal date<input className={field} type="date" required max={new Date().toISOString().slice(0, 10)} value={occurred} onChange={event => setOccurred(event.target.value)} /></label>
      <label className="block text-xs font-semibold">Sales notes<textarea className={field} rows={5} required minLength={10} maxLength={20000} value={notes} onChange={event => setNotes(event.target.value)} placeholder="Paste the conversation or describe why the merchant chose, rejected or left us." /></label>
      <button disabled={busy} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Saving…" : "Save and extract insights"}</button>
    </form> : <div className="mt-5 space-y-4">
      {pending && <p role="status" className="rounded bg-blue-50 p-3 text-sm text-blue-900">Field report saved. Extracting decision drivers and objections… You can close this window; processing will continue.</p>}
      {result.processing_status === "failed" && <div role="alert" className="rounded bg-amber-50 p-3 text-sm"><p>Your report is saved, but extraction could not be completed.</p><button className="mt-2 underline" onClick={() => void retryDeal(result.id).then(setResult).catch(err => setError(err.message))}>Retry extraction</button></div>}
      {result.processing_status === "ready" && <><h3 className="font-bold">Decision drivers</h3>{result.extraction.decision_drivers?.map((item, index) => <article key={index} className="rounded bg-slate-50 p-3 text-sm"><p className="font-semibold">{item.point}</p><blockquote className="mt-1 text-xs text-slate-600">“{item.excerpt}”</blockquote></article>)}{!result.extracted_decision_drivers.length && <p className="text-sm text-slate-600">No explicit decision driver found in these notes.</p>}<p className="text-sm"><strong>Objections:</strong> {result.objections_encountered.join(" · ") || "None recorded"}</p>{result.winning_talk_track && <div className="rounded bg-blue-50 p-3 text-sm"><strong>{result.talk_track_kind === "observed" ? "Reported talk track" : "Suggested pitch — untested"}</strong><p className="mt-1">{result.winning_talk_track}</p></div>}</>}
    </div>}
  </dialog>;
}
