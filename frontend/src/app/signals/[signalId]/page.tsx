"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { LocalErrorBoundary } from "@/components/error-boundary";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import type { LoadState } from "@/lib/types";

type SignalDetailResponse = {
  signal: {
    id: string;
    title: string;
    summary?: string;
    primary_domain?: string;
    urgency_band?: string;
    confidence_band?: string;
    source_name?: string;
    source_url?: string;
    published_at?: string;
    created_at?: string;
    executive_summary?: string;
    financial_impact_indicator?: string;
    key_developments?: string[];
  };
  evidence?: Array<{
    id: string;
    source_name: string;
    source_url?: string;
    published_at?: string;
    is_primary?: boolean;
    tier?: number;
  }>;
  tenant_interpretation?: {
    relevance_band?: string;
    decision_required?: boolean;
    matched_company_objects?: string[];
  };
};

export default function SignalPage() {
  const params = useParams<{ signalId: string }>();
  const signalId = params.signalId;

  return (
    <WorkspaceShell>
      <LocalErrorBoundary fallbackTitle="Signal Telemetry Unavailable">
        <SignalDetailContent signalId={signalId} />
      </LocalErrorBoundary>
    </WorkspaceShell>
  );
}

function SignalDetailContent({ signalId }: { signalId: string }) {
  const router = useRouter();
  const [state, setState] = useState<LoadState<SignalDetailResponse>>({ status: "loading" });

  const loadSignal = useCallback(async () => {
    try {
      setState({ status: "loading" });
      const data = await apiRequest<SignalDetailResponse>(`/api/v1/signals/${signalId}`);
      setState({ status: "ready", data });
    } catch (err) {
      setState({
        status: "error",
        message: err instanceof Error ? err.message : "This intelligence signal could not be retrieved.",
      });
    }
  }, [signalId]);

  useEffect(() => {
    void loadSignal();
  }, [loadSignal]);

  if (state.status === "loading") {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <ModuleLoading label="Loading verified signal telemetry..." />
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <ModuleFailure message={state.message} retry={() => void loadSignal()} />
      </div>
    );
  }

  const { signal, evidence = [], tenant_interpretation } = state.data;
  const isCritical = signal.urgency_band === "CRITICAL" || signal.urgency_band === "HIGH";

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      {/* Back breadcrumb */}
      <div>
        <Link
          href="/radar"
          className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-slate-800 transition"
        >
          <span>←</span> Back to Radar Telemetry
        </Link>
      </div>

      {/* Signal Header Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-[0_1px_2px_rgba(0,0,0,0.05)] space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${
                isCritical
                  ? "bg-red-50 text-red-700 border border-red-200"
                  : "bg-blue-50 text-blue-700 border border-blue-200"
              }`}
            >
              {signal.urgency_band || "MONITOR"}
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono text-slate-500 bg-slate-100 border border-slate-200">
              {signal.primary_domain?.replaceAll("_", " ") || "ECOSYSTEM"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => router.push(`/workspace?query=${encodeURIComponent(signal.title)}`)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 shadow-2xs transition"
            >
              <span>Investigate in Copilot</span>
              <span>⚡</span>
            </button>
            <Link
              href="/artifacts"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 shadow-2xs transition"
            >
              <span>View Decision Units</span>
              <span>→</span>
            </Link>
          </div>
        </div>

        <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight leading-tight">
          {signal.title}
        </h1>

        {signal.summary && (
          <p className="text-sm text-slate-700 leading-relaxed font-medium">
            {signal.summary}
          </p>
        )}

        <div className="pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 font-mono">
          <span>Source: {signal.source_name || "Central Bank of Nigeria / Regulatory Gazette"}</span>
          <span>Verified: {signal.published_at ? new Date(signal.published_at).toLocaleDateString() : "Live Telemetry"}</span>
        </div>
      </div>

      {/* Tenant Exposure Interpretation */}
      {tenant_interpretation && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/70 p-6 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-blue-900">
              Direct Tenant Exposure Assessment
            </span>
            <span className="text-xs font-bold font-mono text-blue-700">
              Relevance: {tenant_interpretation.relevance_band || "HIGH"}
            </span>
          </div>
          <p className="text-xs text-slate-700 leading-relaxed font-medium">
            Matched against your configured active clearing rails and operating licenses.
            {tenant_interpretation.matched_company_objects?.length ? (
              <span className="block mt-1">
                Triggered by dependencies: <strong className="font-semibold text-blue-900">{tenant_interpretation.matched_company_objects.join(", ")}</strong>
              </span>
            ) : null}
          </p>
        </div>
      )}

      {/* Corroborating Primary Sources */}
      {evidence.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_1px_2px_rgba(0,0,0,0.05)] space-y-4">
          <h2 className="text-sm font-bold text-slate-900 tracking-tight uppercase tracking-wider text-xs">
            Verified Primary Sources & Evidence Bundle
          </h2>
          <div className="space-y-2.5">
            {evidence.map((ev, idx) => (
              <div
                key={ev.id || idx}
                className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/60 flex items-center justify-between gap-4 text-xs"
              >
                <div>
                  <span className="font-bold text-slate-800 block">{ev.source_name}</span>
                  {ev.source_url && (
                    <a
                      href={ev.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline text-[11px] truncate block max-w-md font-mono"
                    >
                      {ev.source_url}
                    </a>
                  )}
                </div>
                <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-bold bg-white text-slate-600 border border-slate-200">
                  {ev.is_primary ? "Primary Gazette" : "Corroborated"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
