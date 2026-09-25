"use client";

import { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LocalErrorBoundary } from "@/components/error-boundary";
import { TelemetrySkeleton } from "@/components/skeletons";
import { WorkspaceShell } from "@/components/workspace-shell";
import {
  getOnboardingStatus,
  getRadarSignals,
  getTelemetry,
  listArtifacts,
} from "@/lib/api";
import type {
  IntelligenceArtifact,
  OnboardingStatus,
  TelemetryData,
} from "@/lib/types";

type SignalItem = {
  id: string;
  title: string;
  summary?: string;
  primary_domain: string;
  urgency_band: string;
  confidence_band: string;
  created_at: string;
  source_count?: number;
  corroboration_strength?: string;
  source_name?: string;
  source_url?: string;
};

export default function RadarPage() {
  return (
    <WorkspaceShell>
      <LocalErrorBoundary fallbackTitle="Radar Telemetry Feed Unavailable">
        <RadarContent />
      </LocalErrorBoundary>
    </WorkspaceShell>
  );
}

function RadarContent() {
  const router = useRouter();
  const [, startTransition] = useTransition();

  const [loading, setLoading] = useState(true);
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [signals, setSignals] = useState<SignalItem[]>([]);
  const [artifacts, setArtifacts] = useState<IntelligenceArtifact[]>([]);
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [domainFilter, setDomainFilter] = useState<string>("ALL");
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  // Urgent action checklist state (optimistic)
  const [urgentTasks, setUrgentTasks] = useState([
    {
      id: "tsk-1",
      title: "File updated operational SOP with CBN Consumer Protection Dept",
      deadline: "Day 7",
      owner: "Compliance Director",
      completed: false,
    },
    {
      id: "tsk-2",
      title: "Enforce dual-approval threshold for batch virtual account settlements",
      deadline: "Day 14",
      owner: "Head of Settlement",
      completed: false,
    },
    {
      id: "tsk-3",
      title: "Activate failover routing probe to Wema ALAT Secondary Rail",
      deadline: "Immediate",
      owner: "Lead Platform Engineer",
      completed: true,
    },
  ]);

  async function loadData() {
    try {
      const [telemRes, signalsRes, artifactsRes, statusRes] = await Promise.all([
        getTelemetry(),
        getRadarSignals({ limit: 20 }),
        listArtifacts({ limit: 10 }),
        getOnboardingStatus().catch(() => null),
      ]);

      setTelemetry(telemRes);
      const rawSignals = (signalsRes.signals || signalsRes.items || []) as SignalItem[];
      setSignals(rawSignals);
      setArtifacts(artifactsRes.items || []);
      if (statusRes) setOnboarding(statusRes);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error("Failed to load radar intelligence:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
    // Auto refresh pulse every 30 seconds
    const timer = setInterval(() => {
      void loadData();
    }, 30000);
    return () => clearInterval(timer);
  }, []);

  function toggleTask(id: string) {
    setUrgentTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t))
    );
  }

  const filteredSignals = signals.filter((sig) => {
    if (domainFilter === "ALL") return true;
    return sig.primary_domain?.toUpperCase().includes(domainFilter.toUpperCase());
  });

  return (
    <div className="space-y-8 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Top Banner / Pulse Status */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
            </span>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Live Ecosystem Radar · Pulse Active
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              Updated {lastRefreshed.toLocaleTimeString()}
            </span>
          </div>
          <h1 className="mt-2 text-2xl sm:text-3xl font-black tracking-tight text-slate-900">
            {onboarding?.organization_name
              ? `${onboarding.organization_name} Operational Telemetry`
              : "Executive Radar & Threat Monitor"}
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-slate-600 max-w-3xl">
            Real-time multi-node rail health, promoted CBN circulars, and prioritized commercial counter-measures grounded in tenant license dependencies.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/artifacts"
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-slate-800 transition"
          >
            <span>Browse 3 Decision Units</span>
            <span className="text-blue-400 font-bold">({artifacts.length}) →</span>
          </Link>
          <Link
            href="/workspace"
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-blue-700 transition"
          >
            <span>Open Executive Copilot</span>
            <span>⚡</span>
          </Link>
        </div>
      </div>

      {/* Real-Time Telemetry Node Row */}
      {loading ? (
        <TelemetrySkeleton />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {(telemetry?.nodes || []).map((node, idx) => {
            const isDegraded = node.status === "DEGRADED" || node.status === "OUTAGE";
            return (
              <div
                key={idx}
                className={`rounded-2xl border p-5 transition-all shadow-[0_1px_2px_rgba(0,0,0,0.05)] ${
                  isDegraded
                    ? "border-red-300 bg-red-50/70"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 truncate max-w-[170px]">
                    {node.name}
                  </span>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                      isDegraded
                        ? "bg-red-600 text-white animate-pulse"
                        : "bg-emerald-100 text-emerald-800"
                    }`}
                  >
                    {node.status}
                  </span>
                </div>

                <div className="mt-3 flex items-baseline justify-between font-mono">
                  <div>
                    <span className="text-2xl font-black tracking-tight text-slate-900">
                      {node.latency_ms} <span className="text-xs font-medium text-slate-500">ms</span>
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold text-slate-700">
                      {node.success_rate_pct}%
                    </span>
                    <span className="block text-[10px] text-slate-400">uptime</span>
                  </div>
                </div>

                {isDegraded && node.volume_at_risk_naira && (
                  <div className="mt-3 pt-3 border-t border-red-200/80 flex items-center justify-between text-xs text-red-900 font-medium">
                    <span>At-Risk GMV:</span>
                    <span className="font-mono font-bold">
                      ₦{node.volume_at_risk_naira.toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Main Grid: Urgent Checklist & Live Decision Units Highlight */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column (2 Cols): Critical Signals & Circulars */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Active Telemetry Stream & Regulatory Gazettes
            </h2>

            {/* Filter Pills */}
            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-100 border border-slate-200 overflow-x-auto">
              {[
                { id: "ALL", label: "All Telemetry" },
                { id: "REGULATORY", label: "Regulatory" },
                { id: "INFRASTRUCTURE", label: "Rail Stress" },
                { id: "COMPETITIVE", label: "Competitor" },
              ].map((pill) => (
                <button
                  key={pill.id}
                  type="button"
                  onClick={() => setDomainFilter(pill.id)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                    domainFilter === pill.id
                      ? "bg-white text-slate-900 shadow-2xs font-bold"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {pill.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-3.5">
            {filteredSignals.length === 0 ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center space-y-3">
                <p className="text-sm font-semibold text-slate-700">
                  No telemetry signals matching the current filter.
                </p>
                <button
                  type="button"
                  onClick={() => setDomainFilter("ALL")}
                  className="text-xs font-bold text-blue-600 hover:underline"
                >
                  Reset filter to view all
                </button>
              </div>
            ) : (
              filteredSignals.map((signal) => {
                const isCritical =
                  signal.urgency_band === "CRITICAL" || signal.urgency_band === "HIGH";
                return (
                  <div
                    key={signal.id}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.05)] hover:border-slate-300 hover:shadow-[0_4px_12px_rgba(0,0,0,0.06)] transition"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            isCritical
                              ? "bg-red-50 text-red-700 border border-red-200"
                              : "bg-blue-50 text-blue-700 border border-blue-200"
                          }`}
                        >
                          {signal.urgency_band || "MONITOR"}
                        </span>
                        <span className="text-[11px] font-mono text-slate-500">
                          {signal.primary_domain?.replaceAll("_", " ")}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-400 font-mono">
                        {new Date(signal.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    <h3 className="mt-2 text-sm font-bold text-slate-900 tracking-tight leading-snug">
                      {signal.title}
                    </h3>
                    {signal.summary && (
                      <p className="mt-1 text-xs text-slate-600 leading-relaxed line-clamp-2">
                        {signal.summary}
                      </p>
                    )}

                    <div className="mt-3.5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                      <span className="text-slate-500 text-[11px]">
                        Corroboration: <strong className="text-slate-700">{signal.corroboration_strength || "VERIFIED"}</strong>
                      </span>
                      <button
                        type="button"
                        onClick={() => {
                          startTransition(() => {
                            router.push(`/workspace?query=${encodeURIComponent(signal.title)}`);
                          });
                        }}
                        className="font-bold text-blue-600 hover:text-blue-700 inline-flex items-center gap-1"
                      >
                        Investigate in Copilot →
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column (1 Col): Urgent Executive Action Checklist & Top Decision Units */}
        <div className="space-y-6">
          {/* Urgent Checklist Card */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_1px_2px_rgba(0,0,0,0.05)] space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 tracking-tight">
                Urgent Remediation Checklist
              </h3>
              <span className="text-[11px] font-semibold text-slate-500">
                {urgentTasks.filter((t) => t.completed).length} of {urgentTasks.length} Done
              </span>
            </div>

            <div className="space-y-2.5">
              {urgentTasks.map((task) => (
                <label
                  key={task.id}
                  className={`flex items-start gap-3 p-3 rounded-xl border transition cursor-pointer ${
                    task.completed
                      ? "border-emerald-200 bg-emerald-50/40"
                      : "border-slate-200 bg-white hover:bg-slate-50/50"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={task.completed}
                    onChange={() => toggleTask(task.id)}
                    className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                  />
                  <div className="flex-1 min-w-0">
                    <div
                      className={`text-xs font-semibold leading-snug ${
                        task.completed ? "line-through text-slate-400" : "text-slate-800"
                      }`}
                    >
                      {task.title}
                    </div>
                    <div className="mt-1 flex items-center justify-between text-[10px] text-slate-500">
                      <span>Owner: {task.owner}</span>
                      <span className="font-mono font-semibold text-red-600">Due: {task.deadline}</span>
                    </div>
                  </div>
                </label>
              ))}
            </div>

            <Link
              href="/artifacts?type=gap_matrix"
              className="mt-2 block text-center rounded-xl bg-slate-50 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-100 border border-slate-200 transition"
            >
              Open Full Compliance Matrix Audit →
            </Link>
          </div>

          {/* Quick Decision Units Hub */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_1px_2px_rgba(0,0,0,0.05)] space-y-4">
            <h3 className="text-sm font-bold text-slate-900 tracking-tight">
              3 Core Decision Units
            </h3>

            <div className="space-y-2.5">
              <Link
                href="/artifacts?type=gap_matrix"
                className="block p-3.5 rounded-xl border border-slate-200 hover:border-blue-400 hover:bg-blue-50/30 transition group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900 group-hover:text-blue-700">
                    Compliance Gap Matrix
                  </span>
                  <span className="text-[10px] font-bold text-red-600 uppercase bg-red-50 px-2 py-0.5 rounded border border-red-200">
                    Audit
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-slate-500 leading-snug">
                  Zango model: Split-pane circular comparison, live action checks, statutory fine ticker.
                </p>
              </Link>

              <Link
                href="/artifacts?type=battlecard"
                className="block p-3.5 rounded-xl border border-slate-200 hover:border-purple-400 hover:bg-purple-50/30 transition group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900 group-hover:text-purple-700">
                    Competitive Battlecard
                  </span>
                  <span className="text-[10px] font-bold text-purple-700 uppercase bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                    Klue
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-slate-500 leading-snug">
                  Klue model: One-click sales talk track copier, stance toggle, trap-setting accordions.
                </p>
              </Link>

              <Link
                href="/artifacts?type=rail_stress"
                className="block p-3.5 rounded-xl border border-slate-200 hover:border-amber-400 hover:bg-amber-50/30 transition group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900 group-hover:text-amber-700">
                    Rail Stress Monitor
                  </span>
                  <span className="text-[10px] font-bold text-amber-700 uppercase bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                    Telemetry
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-slate-500 leading-snug">
                  CB Insights model: Pulsing degraded heartbeat, failover routing simulator, merchant notices.
                </p>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
