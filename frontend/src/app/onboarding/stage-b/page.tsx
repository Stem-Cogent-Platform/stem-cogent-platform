"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { StemMark } from "@/components/stem-mark";
import { submitStageB } from "@/lib/api";

type DecisionLens =
  | "executive_strategy"
  | "compliance_legal"
  | "product_engineering"
  | "treasury_reconciliation";

interface LensOption {
  id: DecisionLens;
  title: string;
  subtitle: string;
  desc: string;
  keyDomains: string[];
}

const FUNCTION_LENSES: LensOption[] = [
  {
    id: "executive_strategy",
    title: "Executive Strategy & C-Suite",
    subtitle: "CEO / Managing Director / Founders",
    desc: "Macro market shifts, competitor capital rounds, license changes, and sovereign policy impacts.",
    keyDomains: ["Macro Policy", "Capital", "Competitor Stance"],
  },
  {
    id: "compliance_legal",
    title: "Compliance, Legal & Risk",
    subtitle: "Chief Compliance Officer / General Counsel",
    desc: "CBN circular enforcement checklists, NDPC data audits, statutory filing deadlines, and sanctions.",
    keyDomains: ["CBN Directives", "NDPC Audits", "Sanctions"],
  },
  {
    id: "treasury_reconciliation",
    title: "Treasury, Settlement & Finance",
    subtitle: "CFO / VP Finance / Head of Treasury",
    desc: "NIP float exposure, FX liquidity corridors, margin compression, and switch settlement outages.",
    keyDomains: ["NIP Float", "FX Liquidity", "Switch Outages"],
  },
  {
    id: "product_engineering",
    title: "Product & Engineering",
    subtitle: "CPO / VP Engineering / Tech Leads",
    desc: "API spec deprecations, switch failovers, card scheme mandates, and fallback routing architecture.",
    keyDomains: ["Switch Failover", "API Specs", "Routing Resiliency"],
  },
];

const SUGGESTED_PRIORITIES = [
  "Proactive CBN circular compliance & statutory filing deadlines",
  "NIP switch uptime resilience and Providus settlement stability",
  "Competitor FX margin compression and cross-border expansion",
  "NDPC data sovereignty audit and open banking readiness",
];

export default function StageBOnboardingPage() {
  const router = useRouter();

  const [selectedLens, setSelectedLens] = useState<DecisionLens>("executive_strategy");
  const [priorityFocus, setPriorityFocus] = useState(
    "Proactive regulatory compliance and switch uptime resilience"
  );
  const [sensitivity, setSensitivity] = useState<
    "CRITICAL_ONLY" | "IMPORTANT_AND_CRITICAL"
  >("IMPORTANT_AND_CRITICAL");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeLensMeta = FUNCTION_LENSES.find((l) => l.id === selectedLens) || FUNCTION_LENSES[0];

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await submitStageB({
        business_function: selectedLens.replace("_", " ").toUpperCase(),
        decision_lens: selectedLens,
        priority_focus: priorityFocus.trim(),
        alert_sensitivity: sensitivity,
      });

      // Instant redirect to live radar feed
      router.push("/radar");
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to save executive lens preferences."
      );
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50/60 text-slate-900 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* Top Enterprise Navigation Header */}
      <header className="sticky top-0 z-30 bg-white/95 backdrop-blur border-b border-slate-200 px-6 sm:px-10 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StemMark compact />
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-900 tracking-tight text-base">
              Stem Cogent
            </span>
            <span className="hidden sm:inline-block text-[11px] font-mono text-slate-400">
              | Role Calibration Engine
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="px-2.5 py-1 text-xs font-bold rounded-md bg-slate-900 text-white">
            Stage B of B
          </span>
          <span className="text-xs font-semibold text-slate-600">
            Personal Executive Lens
          </span>
        </div>
      </header>

      {/* Main Split-Canvas Layout */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-10">
        <form onSubmit={handleSubmit} className="space-y-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left Context Rail: 35% Width (4 of 12 cols) */}
            <aside className="lg:col-span-4 space-y-6 lg:sticky lg:top-20">
              <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-7 shadow-xs space-y-5">
                <div className="space-y-2">
                  <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-[11px] font-bold uppercase tracking-wider border border-blue-200/60">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
                    Role-Specific Synthesis
                  </div>
                  <h1 className="text-2xl font-black tracking-tight text-slate-900">
                    Configure Your Executive Lens
                  </h1>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Personalize how Decision Briefs and actionable implications are synthesized for your exact seat at the executive table.
                  </p>
                </div>

                {/* Real-time Lens Synthesis Preview */}
                <div className="pt-4 border-t border-slate-100 space-y-3">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    Live Lens Calibration
                  </div>
                  <div className="p-4 rounded-xl bg-slate-900 text-white space-y-3 shadow-sm">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400">Accountable Role</span>
                      <span className="font-bold text-blue-400 font-mono text-[11px]">
                        {activeLensMeta.subtitle}
                      </span>
                    </div>
                    <div className="text-sm font-bold tracking-tight">
                      {activeLensMeta.title}
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {activeLensMeta.keyDomains.map((domain) => (
                        <span
                          key={domain}
                          className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-800 text-slate-300 border border-slate-700"
                        >
                          {domain}
                        </span>
                      ))}
                    </div>
                    <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                      <span>Alert Threshold</span>
                      <span className="font-semibold text-emerald-400">
                        {sensitivity === "IMPORTANT_AND_CRITICAL"
                          ? "Important & Critical"
                          : "Critical Only"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Information Card */}
                <div className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200/80 text-[11px] text-blue-900 leading-normal space-y-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <span>⚡ Instant Multi-Seat Collaboration</span>
                  </div>
                  <p>
                    Invited teammates (Legal, Treasury, Engineering) will each calibrate their own executive lens while viewing the same company footprint.
                  </p>
                </div>
              </div>
            </aside>

            {/* Right Canvas Column: 65% Width (8 of 12 cols) with 2-Column modular grid */}
            <div className="lg:col-span-8 space-y-6">
              <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xs space-y-8">
                {error && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 font-medium flex items-center gap-2">
                    <span className="text-red-500 font-bold">✕</span>
                    <span>{error}</span>
                  </div>
                )}

                {/* Section 1: Accountable Function / Role Lens */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-800">
                      1. Primary Accountable Function
                    </label>
                    <span className="text-[11px] text-slate-500 font-medium">
                      Select your operational lens
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    {FUNCTION_LENSES.map((item) => {
                      const active = selectedLens === item.id;
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => setSelectedLens(item.id)}
                          aria-pressed={active}
                          className={`text-left p-4 rounded-xl border transition-all duration-150 flex flex-col justify-between group ${
                            active
                              ? "bg-blue-50/80 text-blue-950 border-blue-600 ring-1 ring-blue-600/30 shadow-xs"
                              : "bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50/70"
                          }`}
                        >
                          <div>
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-bold text-sm text-slate-900 group-hover:text-blue-900">
                                {item.title}
                              </span>
                              <span
                                className={`flex h-4 w-4 shrink-0 items-center justify-center rounded transition-colors ${
                                  active
                                    ? "bg-blue-600 text-white"
                                    : "border border-slate-300 bg-white"
                                }`}
                              >
                                {active && (
                                  <svg
                                    className="h-3 w-3 stroke-current"
                                    viewBox="0 0 12 12"
                                    fill="none"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                  >
                                    <polyline points="2.5 6 4.5 8 9.5 3" />
                                  </svg>
                                )}
                              </span>
                            </div>
                            <div
                              className={`text-[11px] mt-0.5 font-semibold ${
                                active ? "text-blue-700" : "text-slate-500"
                              }`}
                            >
                              {item.subtitle}
                            </div>
                          </div>
                          <p
                            className={`mt-3 text-[11px] leading-relaxed ${
                              active ? "text-blue-900/80" : "text-slate-600"
                            }`}
                          >
                            {item.desc}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Section 2: Immediate Priority Focus */}
                <div className="border-t border-slate-100 pt-6 space-y-3">
                  <label
                    htmlFor="priorityFocus"
                    className="block text-xs font-bold uppercase tracking-wider text-slate-800"
                  >
                    2. Immediate Priority Focus (Current Quarter Vigilance)
                  </label>
                  <input
                    id="priorityFocus"
                    type="text"
                    required
                    value={priorityFocus}
                    onChange={(e) => setPriorityFocus(e.target.value)}
                    placeholder="e.g. CBN open banking compliance, Providus settlement stability"
                    className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-sm font-medium text-slate-900 placeholder-slate-400 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/10 shadow-2xs transition"
                  />
                  <div className="space-y-1.5">
                    <span className="text-[11px] text-slate-500 block font-medium">
                      Suggested priorities (click to populate):
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {SUGGESTED_PRIORITIES.map((suggestion) => (
                        <button
                          key={suggestion}
                          type="button"
                          onClick={() => setPriorityFocus(suggestion)}
                          className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-700 border border-slate-200 transition-colors text-left"
                        >
                          + {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Section 3: Notification Sensitivity */}
                <div className="border-t border-slate-100 pt-6 space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-800">
                      3. Alert Sensitivity Threshold
                    </label>
                    <span className="text-[11px] text-slate-500 font-medium">
                      Control notification velocity
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <button
                      type="button"
                      onClick={() => setSensitivity("IMPORTANT_AND_CRITICAL")}
                      aria-pressed={sensitivity === "IMPORTANT_AND_CRITICAL"}
                      className={`text-left p-4 rounded-xl border transition-all duration-150 flex flex-col justify-between ${
                        sensitivity === "IMPORTANT_AND_CRITICAL"
                          ? "bg-blue-50/80 text-blue-950 border-blue-600 ring-1 ring-blue-600/30 shadow-xs"
                          : "bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50/70"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-slate-900">
                          Important & Critical
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                          Recommended
                        </span>
                      </div>
                      <p className="mt-2 text-[11px] text-slate-600 leading-relaxed">
                        Continuous monitoring. Notifies for direct regulatory changes, competitor capital moves, and upstream switch latency.
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setSensitivity("CRITICAL_ONLY")}
                      aria-pressed={sensitivity === "CRITICAL_ONLY"}
                      className={`text-left p-4 rounded-xl border transition-all duration-150 flex flex-col justify-between ${
                        sensitivity === "CRITICAL_ONLY"
                          ? "bg-blue-50/80 text-blue-950 border-blue-600 ring-1 ring-blue-600/30 shadow-xs"
                          : "bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50/70"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-slate-900">
                          Critical Only
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600">
                          Strict
                        </span>
                      </div>
                      <p className="mt-2 text-[11px] text-slate-600 leading-relaxed">
                        Strict suppression. Only alerts on statutory enforcement fines, license revocation threats, and total clearing outages.
                      </p>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Persistent Bottom Action Bar */}
          <div className="sticky bottom-0 z-20 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-8 py-4 bg-white/90 backdrop-blur-md border-t border-slate-200 shadow-lg">
            <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2.5 text-xs text-slate-600">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-medium">
                  Lens calibrated for {activeLensMeta.subtitle}
                </span>
                <span className="hidden md:inline text-slate-300">•</span>
                <span className="hidden md:inline text-slate-500">
                  Ready to launch live decision workspace
                </span>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full sm:w-auto px-7 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2 disabled:opacity-50 transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-98"
              >
                {loading ? (
                  <span>Synthesizing Live Radar…</span>
                ) : (
                  <>
                    <span>Launch Decision Workspace</span>
                    <span>➔</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </main>
    </div>
  );
}
