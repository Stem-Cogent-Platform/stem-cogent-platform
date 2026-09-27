"use client";

import type { IntelligenceArtifact } from "@/lib/types";

interface Props {
  artifact: IntelligenceArtifact;
  onUpdate?: (updated: IntelligenceArtifact) => void;
}

export function RailStressMonitor({ artifact }: Props) {
  const payload = artifact.payload || {};
  const latency = typeof payload.latency_ms === "number" ? payload.latency_ms : null;
  const exposure = typeof payload.at_risk_volume_naira === "number" ? payload.at_risk_volume_naira : null;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-5">
      <header>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Recorded rail assessment</p>
        <h3 className="mt-2 text-lg font-bold text-slate-900">{artifact.title}</h3>
        <p className="mt-1 text-sm text-slate-600">{payload.impacted_node || "Affected node not specified"}</p>
      </header>
      <dl className="grid gap-4 sm:grid-cols-2 text-sm">
        <div><dt className="text-slate-500">Reported trigger</dt><dd>{payload.telemetry_trigger || "No trigger recorded"}</dd></div>
        <div><dt className="text-slate-500">Operational exposure</dt><dd>{payload.operational_exposure || "No exposure assessment recorded"}</dd></div>
        <div><dt className="text-slate-500">Recorded latency</dt><dd>{latency === null ? "Not measured" : `${latency.toLocaleString()} ms`}</dd></div>
        <div><dt className="text-slate-500">Recorded volume at risk</dt><dd>{exposure === null ? "Not measured" : `₦${exposure.toLocaleString()}`}</dd></div>
        <div><dt className="text-slate-500">Suggested alternative rail</dt><dd>{payload.recommended_fallback_node || "No alternative assessed"}</dd></div>
      </dl>
      <p role="status" className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
        This assessment does not measure current bank health or change payment routing. Live probes and failover execution are not connected. Confirm conditions with your payment provider before taking action.
      </p>
    </section>
  );
}
