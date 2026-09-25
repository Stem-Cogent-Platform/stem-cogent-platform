"use client";

import { useCallback, useEffect, useState } from "react";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { downloadPolicy, getPolicies } from "@/lib/compliance";
import type { PolicyList } from "@/lib/compliance";

const field = "mt-1 w-full rounded-lg border border-slate-300 bg-white p-2 text-sm";

export default function PolicyVaultPage() {
  const [data, setData] = useState<PolicyList>({items: [], health: {assessed_obligations: 0, policy_evidence_score: null}});
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [version, setVersion] = useState("1.0");
  const [category, setCategory] = useState("aml_kyc");
  const [family, setFamily] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => { setData(await getPolicies()); }, []);
  useEffect(() => { void load().catch(err => setError(err.message)); }, [load]);
  const pending = data.items.some(item => ["queued", "processing"].includes(item.processing_status));
  useEffect(() => { if (!pending) return; const timer = setInterval(() => void load().catch(err => setError(err.message)), 4000); return () => clearInterval(timer); }, [pending, load]);
  async function upload(event: React.FormEvent) {
    event.preventDefault(); if (!file) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const body = new FormData(); body.append("file", file); body.append("document_title", title); body.append("version", version); body.append("policy_category", category); if (family) body.append("document_family_id", family);
      await apiRequest("/api/v1/policies/upload", {method: "POST", body, signal: AbortSignal.timeout(120_000)});
      setFile(null); setTitle(""); setNotice("Upload received. Text extraction and indexing are queued."); await load();
    } catch (err) { setError(err instanceof Error ? err.message : "Upload failed"); }
    finally { setBusy(false); }
  }
  return <WorkspaceShell><main className="mx-auto max-w-6xl space-y-6 p-6"><header><p className="text-xs font-semibold uppercase tracking-widest text-blue-700">Company governance</p><h1 className="mt-1 text-3xl font-bold">Policy vault</h1><p className="mt-2 text-sm text-slate-600">Versioned policies and controls used as evidence in your regulatory audits.</p></header>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}{notice && <p role="status" className="rounded-lg bg-blue-50 p-3 text-sm text-blue-900">{notice}</p>}
    <section className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-600">Policy evidence health score</p><p className="mt-1 text-3xl font-bold">{data.health.policy_evidence_score === null ? "Not assessed" : `${Number(data.health.policy_evidence_score).toFixed(0)}%`}</p><p className="mt-1 text-xs text-slate-500">Across {data.health.assessed_obligations} obligations in the latest completed audits. This measures documented evidence, not operational effectiveness.</p></section>
    <form onSubmit={event => void upload(event)} className="space-y-4 rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-bold">Upload a policy or a new version</h2><label onDragOver={event => event.preventDefault()} onDrop={event => {event.preventDefault(); setFile(event.dataTransfer.files[0] ?? null);}} className="block cursor-pointer rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-7 text-center"><span className="block text-sm font-semibold">Drop a PDF or DOCX here, or choose a file</span><span className="mt-1 block text-xs text-slate-500">Up to 20 MB. Scanned PDFs need readable text before they can be assessed.</span><input aria-label="Policy document" type="file" accept=".pdf,.docx" className="mt-3 text-xs" onChange={event => setFile(event.target.files?.[0] ?? null)} />{file && <span className="mt-2 block text-xs">Selected: {file.name}</span>}</label><div className="grid gap-4 sm:grid-cols-2"><label className="text-xs font-semibold">Document title<input className={field} required maxLength={255} value={title} onChange={event => setTitle(event.target.value)} /></label><label className="text-xs font-semibold">Policy family<select className={field} value={family} onChange={event => setFamily(event.target.value)}><option value="">New policy</option>{data.items.filter((item, index, all) => all.findIndex(other => other.document_family_id === item.document_family_id) === index).map(item => <option value={item.document_family_id} key={item.document_family_id}>{item.document_title}</option>)}</select></label><label className="text-xs font-semibold">Version<input className={field} required maxLength={20} value={version} onChange={event => setVersion(event.target.value)} /></label><label className="text-xs font-semibold">Category<select className={field} value={category} onChange={event => setCategory(event.target.value)}>{["aml_kyc", "data_privacy", "payment_ops", "dispute_resolution", "other"].map(value => <option key={value} value={value}>{value.replaceAll("_", " ").toUpperCase()}</option>)}</select></label></div><button disabled={!file || busy} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">{busy ? "Uploading…" : "Upload and index"}</button></form>
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white"><table className="w-full text-left text-sm"><caption className="p-4 text-left font-bold">Policy versions</caption><thead className="border-y border-slate-200 bg-slate-50 text-xs text-slate-500"><tr>{["Policy", "Version", "Status", "Chunks", "Actions"].map(label => <th key={label} className="p-3">{label}</th>)}</tr></thead><tbody>{data.items.map(item => <tr key={item.id} className="border-b border-slate-100"><td className="p-3 font-semibold">{item.document_title}<small className="block font-normal text-slate-500">{item.policy_category.replaceAll("_", " ")}</small></td><td className="p-3">{item.version}{item.active && <span className="ml-2 rounded bg-emerald-50 px-2 py-1 text-xs text-emerald-800">Active</span>}</td><td className="p-3">{item.processing_status.replaceAll("_", " ")}{item.error_code && <small className="block text-red-700">{item.error_code.replaceAll("_", " ")}</small>}</td><td className="p-3">{item.embedded_chunks_count}</td><td className="space-x-3 p-3"><button className="text-blue-700 underline" onClick={() => void downloadPolicy(item.id).catch(err => setError(err.message))}>Download</button>{item.processing_status === "failed" && <button className="text-blue-700 underline" onClick={() => void apiRequest(`/api/v1/policies/${item.id}/retry`, {method: "POST"}).then(load).catch(err => setError(err.message))}>Retry</button>}</td></tr>)}</tbody></table>{!data.items.length && <p className="p-6 text-center text-sm text-slate-500">No policies uploaded yet.</p>}</div>
  </main></WorkspaceShell>;
}
