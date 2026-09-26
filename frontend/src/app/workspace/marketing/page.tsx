"use client";

import { useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import type { MarketingResult } from "@/lib/compliance";

export default function MarketingCheckerPage() {
  const [copy, setCopy] = useState("");
  const [checkedCopy, setCheckedCopy] = useState("");
  const [checkedChannel, setCheckedChannel] = useState("");
  const [channel, setChannel] = useState("social");
  const [result, setResult] = useState<MarketingResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function check(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError(""); setResult(null);
    try { const value = await apiRequest<MarketingResult>("/api/v1/workspace/marketing/check", {method: "POST", body: JSON.stringify({copy, channel})}); setResult(value); setCheckedCopy(copy); setCheckedChannel(channel); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not check campaign"); }
    finally { setBusy(false); }
  }
  const characters = Array.from(checkedCopy);
  const spans: Array<{text: string; flagged: boolean}> = [];
  characters.forEach((character, index) => {
    const flagged = result?.findings.some(finding => index >= finding.start && index < finding.end) ?? false;
    const last = spans[spans.length - 1]; if (last && last.flagged === flagged) last.text += character; else spans.push({text: character, flagged});
  });
  return <WorkspaceShell><main className="mx-auto max-w-5xl space-y-6 p-6"><header><p className="text-xs font-semibold uppercase tracking-widest text-blue-700">Decision workspace</p><h1 className="mt-1 text-3xl font-bold">Campaign compliance checker</h1><p className="mt-2 text-sm text-slate-600">Screen promotional claims against selected Nigerian advertising rules, inspect citations, and review alternative wording.</p></header>
    <form className="space-y-4 rounded-xl border border-slate-200 bg-white p-5" onSubmit={event => void check(event)}><label className="block text-sm font-semibold">Campaign copy<textarea className="mt-2 w-full rounded-lg border border-slate-300 p-3 text-sm" rows={9} minLength={10} maxLength={15000} required value={copy} onChange={event => setCopy(event.target.value)} placeholder="Paste campaign, SMS or landing page copy…" /></label><div className="flex items-end justify-between gap-4"><label className="text-xs font-semibold">Channel<select className="ml-3 rounded-lg border border-slate-300 p-2" value={channel} onChange={event => setChannel(event.target.value)}>{["social", "sms", "email", "landing_page", "other"].map(value => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label><button disabled={busy || copy.trim().length < 10} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">{busy ? "Checking…" : "Check campaign"}</button></div></form>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
    {result && <section className="space-y-4" aria-live="polite"><div className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-bold">{result.findings.length ? `${result.findings.length} findings to review` : "No flags in the checked rules"}</h2><p className="mt-2 text-xs text-slate-600">{result.scope}</p>{(copy !== checkedCopy || channel !== checkedChannel) && <p className="mt-2 text-xs text-amber-800">Copy or channel has changed. Run the checker again to assess your edits.</p>}<div className="mt-4 whitespace-pre-wrap text-sm leading-7">{spans.map((span, index) => span.flagged ? <mark key={index} className="rounded bg-amber-100 px-0.5 text-amber-950">{span.text}</mark> : <span key={index}>{span.text}</span>)}</div></div>{result.findings.map((finding, index) => <article key={index} className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-xs font-bold uppercase text-amber-800">{finding.severity} · {finding.rule_id.replaceAll("_", " ")}</p><h3 className="mt-2 text-sm font-semibold">{finding.reason}</h3><a href={finding.source_url} target="_blank" rel="noreferrer" className="mt-2 block text-xs text-blue-700 underline">{finding.reference}</a><div className="mt-4 rounded-lg bg-slate-50 p-3"><p className="text-xs font-bold text-slate-500">Suggested wording — human review required</p><p className="mt-2 text-sm">{finding.suggested_alternative}</p></div></article>)}<p className="text-xs text-slate-500">Rules version {result.rules_version}</p></section>}
  </main></WorkspaceShell>;
}
