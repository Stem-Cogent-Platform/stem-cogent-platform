"use client";

import { FormEvent, useState } from "react";

import { apiRequest } from "@/lib/api";

type Citation = { source_signal_id: string; source_name: string; source_url?: string };
type Response = { answer_text: string; citations: Citation[]; confidence_indicator: string; follow_up_suggestions: string[] };

export function CILPanel({ anchorId, anchorType = "DECISION_BRIEF" }: { anchorId: string; anchorType?: "DECISION_BRIEF" | "SIGNAL" | "ENTITY" | "COMPANY_LENS" }) {
  const [result, setResult] = useState<Response | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const suggested = anchorType === "ENTITY"
    ? ["What changed recently?", "Which relationships matter most?"]
    : ["What evidence supports this?", "What decision is required?", "What remains uncertain?"];

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true); setMessage("");
    try {
      setResult(await apiRequest<Response>("/api/v1/cil/query", { method: "POST", body: JSON.stringify({ query: form.get("query"), anchor_type: anchorType, anchor_id: anchorId }) }));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Cogent could not investigate this item right now.");
    } finally { setSaving(false); }
  }

  return (
    <aside className="cil-panel">
      <p className="eyebrow">Investigate with Cogent</p>
      <h2>Grounded follow-up</h2>
      <p className="cil-scope">Answers stay anchored to this item and cite the evidence used.</p>
      <div className="cil-suggestions">{suggested.map((item) => <button key={item} onClick={() => setQuery(item)} type="button">{item}</button>)}</div>
      <form onSubmit={submit}><label><span>Question about this evidence</span><textarea name="query" minLength={3} onChange={(event) => setQuery(event.target.value)} placeholder="What evidence supports the deadline?" required value={query} /></label><button className="primary-button" disabled={saving || query.trim().length < 3} type="submit">{saving ? "Reviewing evidence…" : "Ask Cogent"}</button></form>
      {message && <p className="form-message">{message}</p>}
      {result && <section className="cil-answer"><span className="verified-chip">{result.confidence_indicator} confidence</span><p>{result.answer_text}</p><h3>Verified evidence</h3><ul>{result.citations.map((citation) => <li key={citation.source_signal_id}>{citation.source_url ? <a href={citation.source_url} rel="noreferrer" target="_blank">{citation.source_name}</a> : citation.source_name}</li>)}</ul>{result.follow_up_suggestions.length > 0 && <><h3>Continue investigating</h3><div className="cil-suggestions">{result.follow_up_suggestions.map((item) => <button key={item} onClick={() => setQuery(item)} type="button">{item}</button>)}</div></>}</section>}
    </aside>
  );
}
