"use client";

import type { Citation, EvidenceSource, ResearchResult } from "@/lib/competitors";

export function Citations({citations, sources}: {citations: Citation[]; sources: EvidenceSource[]}) {
  return <details className="mt-2 text-xs text-slate-600"><summary className="cursor-pointer font-semibold text-blue-700">Supporting evidence ({citations.length})</summary>
    {citations.map((citation, index) => {
      const source = sources.find(item => item.id === citation.source_id);
      return <div key={index} className="mt-3 border-l-2 border-blue-200 pl-3"><blockquote className="whitespace-pre-wrap">{citation.excerpt}</blockquote>
        {source?.url ? <a href={source.url} target="_blank" rel="noreferrer" className="mt-1 block underline">{source.title}</a> : <p className="mt-1 font-medium">{source?.title ?? citation.source_id} · Internal evidence</p>}
      </div>;
    })}
  </details>;
}

export function CompetitiveResearchResult({result}: {result: ResearchResult}) {
  return <section aria-label="Competitive research results" className="space-y-4 rounded-xl border border-blue-200 bg-white p-5">
    <h2 className="text-lg font-bold">Competitive research</h2>
    <p className="text-xs text-slate-600">{result.filters.competitor_name || "All competitors"} · {result.filters.merchant_segment || "All segments"} · {result.filters.start_date || "Earliest record"} to {result.filters.end_date || "Latest record"}</p>
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{[["Won", result.metrics.won], ["Lost", result.metrics.lost], ["Churned", result.metrics.churned], ["Win rate", result.metrics.win_rate === null ? "Not established" : `${result.metrics.win_rate}%`]].map(([label, value]) => <div className="rounded-lg bg-slate-50 p-3" key={label}><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-lg font-bold">{value}</p></div>)}</div>
    <p className="text-xs text-slate-500">{result.metric_definition}</p>
    {result.status !== "ready" && <p role="status" className="rounded bg-amber-50 p-3 text-sm text-amber-900">{result.status === "no_evidence" ? "No supporting evidence is available for this scope yet." : "Narrative synthesis is unavailable. Counts and evidence are shown below."}</p>}
    {result.playbook.findings.map((claim, index) => <article key={index} className="border-t border-slate-100 pt-3"><p className="text-sm">{claim.value}</p><Citations citations={claim.citations} sources={result.sources} /></article>)}
    {result.playbook.recommended_actions.length > 0 && <h3 className="text-sm font-semibold">Suggested playbook — validate before use</h3>}
    {result.playbook.recommended_actions.map((claim, index) => <article key={index} className="rounded-lg bg-blue-50 p-3 text-sm"><p>{claim.value}</p><Citations citations={claim.citations} sources={result.sources} /></article>)}
    {[...result.scope_notes, ...result.playbook.limitations].map((note, index) => <p key={index} className="text-xs text-amber-900">{note}</p>)}
    <details className="text-xs"><summary className="cursor-pointer font-semibold">Research sources ({result.sources.length})</summary>{result.sources.map(source => <div key={source.id} className="mt-3"><p className="font-medium">{source.title}</p>{source.url && <a className="text-blue-700 underline" href={source.url} target="_blank" rel="noreferrer">Open public source</a>}<p className="mt-1 whitespace-pre-wrap text-slate-600">{source.text}</p></div>)}</details>
  </section>;
}
