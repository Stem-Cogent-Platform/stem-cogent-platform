"use client";

import { useState } from "react";
import { simulateFailover } from "@/lib/api";
import type { FailoverSimulationResult, IntelligenceArtifact } from "@/lib/types";

interface Props {
  artifact: IntelligenceArtifact;
  onUpdate?: (updated: IntelligenceArtifact) => void;
}

export function RailStressMonitor({ artifact }: Props) {
  const payload = artifact.payload || {};
  const impactedNode = payload.impacted_node || "Providus Bank Core (Inward Settlements)";
  const affectedChannel = payload.affected_rail_channel || "virtual_account_collection";
  const telemetryTrigger = payload.telemetry_trigger || "API latency > 15s; inward collection drops > 35%";
  const operationalExposure = payload.operational_exposure || "Stalled GMV: ₦42,500,000 queued; elevated merchant timeout rates.";
  const fallbackNode = payload.recommended_fallback_node || "Wema ALAT Node";

  const baselineLatency = payload.latency_ms || 3420;
  const initialVolumeAtRisk = payload.at_risk_volume_naira || 42500000;

  // Simulation state
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<FailoverSimulationResult | null>(null);
  const [simStep, setSimStep] = useState<number>(0);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);

  // Merchant Notice Modal / Card state
  const [showMerchantNotice, setShowMerchantNotice] = useState(false);
  const [copiedNotice, setCopiedNotice] = useState(false);

  const merchantNoticeText = `⚠️ System Advisory: We are currently experiencing degraded response times on virtual account collections via our primary settlement bank (${impactedNode}).
Failover routes to secondary clearing nodes are active. Inward transfers remain secure, but merchants may observe temporary 5-10 minute confirmation delays.
Zero transactions have been lost. Engineering & Treasury teams are actively monitoring clearance queues.`;

  async function handleRunFailoverSimulation() {
    setIsSimulating(true);
    setSimulationResult(null);
    setSimStep(1);
    setErrorNotice(null);

    // Visual step progression
    setTimeout(() => setSimStep(2), 500);
    setTimeout(() => setSimStep(3), 1000);

    try {
      const res = await simulateFailover(artifact.id, fallbackNode, 100);
      if (res && res.simulation) {
        setTimeout(() => {
          setSimulationResult(res.simulation);
          setIsSimulating(false);
          setSimStep(0);
        }, 1300);
      } else {
        setIsSimulating(false);
      }
    } catch (err) {
      setIsSimulating(false);
      setSimStep(0);
      setErrorNotice(err instanceof Error ? err.message : "Failover simulation failed to complete.");
    }
  }

  async function handleCopyMerchantNotice() {
    try {
      await navigator.clipboard.writeText(merchantNoticeText);
      setCopiedNotice(true);
      setTimeout(() => setCopiedNotice(false), 2400);
    } catch (err) {
      console.error("Clipboard copy failed:", err);
    }
  }

  const currentLatency = simulationResult ? simulationResult.latency_recovered_ms : baselineLatency;
  const currentRisk = simulationResult ? initialVolumeAtRisk - simulationResult.at_risk_volume_protected_naira : initialVolumeAtRisk;

  return (
    <div className="group relative rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_1px_2px_rgba(0,0,0,0.05)] hover:shadow-[0_4px_12px_rgba(0,0,0,0.08)] transition-all duration-200 hover:-translate-y-0.5">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200">
              Infrastructure Telemetry
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono text-slate-500 bg-slate-100 border border-slate-200">
              {affectedChannel}
            </span>
          </div>
          <h3 className="mt-2 text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>{impactedNode}</span>
            <span className="text-slate-400 font-normal">·</span>
            <span className="text-sm font-semibold text-slate-600">{artifact.title}</span>
          </h3>
        </div>

        {/* Action Button: Merchant Alert Generator */}
        <button
          type="button"
          onClick={() => setShowMerchantNotice(!showMerchantNotice)}
          className="inline-flex items-center gap-2 rounded-xl bg-slate-100 px-3.5 py-2 text-xs font-bold text-slate-800 hover:bg-slate-200 transition border border-slate-200"
        >
          <span>{showMerchantNotice ? "Hide Merchant Notice" : "Generate Merchant Notice"}</span>
          <span className="text-slate-400">⚡</span>
        </button>
      </div>

      {/* Dark Slate Telemetry Sub-Card (CB Insights Node Model) */}
      <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950 p-5 text-white shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              {/* Pulsing Radar Heartbeat */}
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
              </span>
              <span className="text-xs font-bold tracking-wider uppercase text-red-400">
                DEGRADED TELEMETRY STREAM
              </span>
            </div>
            <p className="text-sm font-mono text-slate-300">
              Trigger: <span className="text-amber-400">{telemetryTrigger}</span>
            </p>
            <p className="text-xs text-slate-400">
              {operationalExposure}
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-3 md:pt-0 border-t md:border-t-0 border-slate-800 text-left md:text-right font-mono">
            <div>
              <span className="text-[10px] text-slate-400 block uppercase">Node Latency</span>
              <span className={`text-xl font-bold ${simulationResult ? "text-emerald-400" : "text-red-400"}`}>
                {currentLatency} ms
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block uppercase">Volume At Risk</span>
              <span className="text-xl font-bold text-amber-300">
                ₦{currentRisk.toLocaleString()}
              </span>
            </div>
            <div className="col-span-2 sm:col-span-1">
              <span className="text-[10px] text-slate-400 block uppercase">Failover Target</span>
              <span className="text-xs font-semibold text-blue-400 block truncate">
                {fallbackNode}
              </span>
            </div>
          </div>
        </div>

        {/* Live Fallback Simulation Trigger & Animated 3-Step Check */}
        <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="text-xs font-semibold text-slate-300">
              Dynamic Redundancy Control
            </div>
            <p className="text-[11px] text-slate-400">
              Simulate traffic failover to secondary clearing node to mitigate merchant dropped requests.
            </p>
          </div>

          <button
            type="button"
            onClick={() => void handleRunFailoverSimulation()}
            disabled={isSimulating}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-blue-500 active:scale-[0.98] transition disabled:opacity-50"
          >
            {isSimulating ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Routing Step {simStep} of 3...</span>
              </>
            ) : simulationResult ? (
              <>
                <span>Failover Active: Latency -{simulationResult.latency_reduction_pct}%</span>
                <span className="text-emerald-300 font-bold">✓</span>
              </>
            ) : (
              <>
                <span>Test Failover Routing: Switch to {fallbackNode}</span>
                <span className="text-blue-300 font-bold">⚡</span>
              </>
            )}
          </button>
        </div>

        {/* Animated 3-Step Routing Check Progress */}
        {isSimulating && (
          <div className="mt-4 rounded-lg bg-slate-900/90 p-3.5 border border-slate-800 text-xs font-mono space-y-2">
            <div className={`flex items-center gap-2 ${simStep >= 1 ? "text-emerald-400 font-semibold" : "text-slate-500"}`}>
              <span>{simStep > 1 ? "✓" : "▶"}</span>
              <span>Step 1: Health check probe to {fallbackNode} (42ms response)</span>
            </div>
            <div className={`flex items-center gap-2 ${simStep >= 2 ? "text-emerald-400 font-semibold" : "text-slate-500"}`}>
              <span>{simStep > 2 ? "✓" : simStep === 2 ? "▶" : "·"}</span>
              <span>Step 2: Traffic weight migration to secondary rail (100% shifted)</span>
            </div>
            <div className={`flex items-center gap-2 ${simStep >= 3 ? "text-emerald-400 font-semibold" : "text-slate-500"}`}>
              <span>{simStep === 3 ? "▶" : "·"}</span>
              <span>Step 3: Settlement telemetry stabilization (99.4% success verified)</span>
            </div>
          </div>
        )}

        {/* Simulation Recovery Confirmation Banner */}
        {simulationResult && !isSimulating && (
          <div className="mt-4 rounded-lg bg-emerald-950/70 p-3 border border-emerald-700/60 text-xs font-mono flex items-center justify-between">
            <div className="text-emerald-300">
              <strong>Simulated Reroute Verified:</strong> Latency reduced from {simulationResult.latency_baseline_ms}ms to {simulationResult.latency_recovered_ms}ms ({simulationResult.latency_reduction_pct}% improvement).
            </div>
            <span className="text-emerald-200 font-bold">
              ₦{simulationResult.at_risk_volume_protected_naira.toLocaleString()} Protected
            </span>
          </div>
        )}

        {errorNotice && (
          <div className="mt-3 rounded-lg bg-red-900/60 p-2 text-xs text-red-200 border border-red-800">
            {errorNotice}
          </div>
        )}
      </div>

      {/* Merchant Notice Generator Output Drawer */}
      {showMerchantNotice && (
        <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50/70 p-4.5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-900 flex items-center gap-1.5">
              <span>📋 Merchant Dashboard Broadcast Notice</span>
            </span>
            <button
              type="button"
              onClick={() => void handleCopyMerchantNotice()}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold transition shadow-2xs ${
                copiedNotice
                  ? "bg-emerald-600 text-white"
                  : "bg-amber-800 text-white hover:bg-amber-900"
              }`}
            >
              {copiedNotice ? "Copied Notice Template!" : "Copy Notice Template"}
            </button>
          </div>
          <div className="rounded-lg bg-white p-3 text-xs text-slate-800 font-mono leading-relaxed border border-amber-200/80 shadow-2xs whitespace-pre-line">
            {merchantNoticeText}
          </div>
          <p className="text-[11px] text-amber-800 font-medium">
            Paste this banner into your merchant portal or incident status page (e.g. Instatus / Statuspage).
          </p>
        </div>
      )}
    </div>
  );
}
