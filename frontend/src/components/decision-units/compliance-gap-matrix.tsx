"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { updateActionItemStatus } from "@/lib/api";
import type { ActionItem, IntelligenceArtifact } from "@/lib/types";

export function ComplianceGapMatrix({artifact, onUpdate}: {artifact: IntelligenceArtifact; onUpdate?: (value: IntelligenceArtifact) => void}) {
  const payload = artifact.payload;
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  useEffect(() => {
    const state = payload.remediation_state || {};
    setActions((payload.corrective_actions || payload.action_plan || payload.checklist || []).map((item: ActionItem, index: number) => {
      const id = item.id || item.action_id || `act-${index}`;
      return {...item, id, completed: state[id]?.completed ?? Boolean(item.completed)};
    }));
  }, [payload]);
  async function toggle(item: ActionItem) {
    const id = item.id || "";
    setBusy(id); setError("");
    try {
      const updated = await updateActionItemStatus(artifact.id, id, !item.completed);
      if (updated?.payload) onUpdate?.({...artifact, payload: updated.payload});
      setActions(previous => previous.map(action => action.id === id ? {...action, completed: !item.completed} : action));
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update action"); }
    finally { setBusy(""); }
  }
  return <article className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
    <header><p className="text-xs font-semibold uppercase text-slate-500">Regulatory summary</p><h3 className="mt-1 text-lg font-bold">{artifact.title}</h3><p className="text-xs text-slate-500">{payload.circular_reference}</p></header>
    <p className="text-sm text-slate-700">{payload.statutory_mandate}</p>
    <p className="text-xs text-slate-500">This summary is separate from the evidence assessment in the obligations register.</p>
    {payload.statutory_fine_exposure && <p className="text-sm">Source-reported sanction: {payload.statutory_fine_exposure}</p>}
    {payload.statutory_deadline && <p className="text-sm">Source-reported deadline: {payload.statutory_deadline}</p>}
    <Link className="block text-sm font-semibold text-blue-700 underline" href={`/artifacts?type=gap_matrix&signal_id=${encodeURIComponent(artifact.signal_id)}`}>Review supporting evidence</Link>
    {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
    {actions.length > 0 && <fieldset className="space-y-2"><legend className="mb-2 text-sm font-bold">Remediation actions</legend>{actions.map(item => <label key={item.id} className="flex gap-3 text-sm"><input type="checkbox" checked={Boolean(item.completed)} disabled={busy === item.id} onChange={() => void toggle(item)} /><span>{item.action}<small className="block text-slate-500">{item.accountable_role}{item.deadline ? ` ? ${item.deadline}` : ""}</small></span></label>)}</fieldset>}
  </article>;
}
