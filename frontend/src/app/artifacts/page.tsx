"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { LocalErrorBoundary } from "@/components/error-boundary";
import { GapMatrixSkeleton } from "@/components/skeletons";
import { ComplianceGapMatrix } from "@/components/decision-units/compliance-gap-matrix";
import { EvidenceReviewer } from "@/components/decision-units/evidence-reviewer";
import { CompetitiveBattlecard } from "@/components/decision-units/competitive-battlecard";
import { RailStressMonitor } from "@/components/decision-units/rail-stress-monitor";
import { WorkspaceShell } from "@/components/workspace-shell";
import { listArtifacts } from "@/lib/api";
import type { IntelligenceArtifact } from "@/lib/types";

export default function ArtifactsPage() {
  return (
    <WorkspaceShell>
      <LocalErrorBoundary fallbackTitle="Decision Artifacts Engine Unavailable">
        <Suspense fallback={<GapMatrixSkeleton />}>
          <ArtifactsContent />
        </Suspense>
      </LocalErrorBoundary>
    </WorkspaceShell>
  );
}

type TabKey = "ALL" | "gap_matrix" | "battlecard" | "rail_stress";

function ArtifactsContent() {
  const searchParams = useSearchParams();
  const initialType = (searchParams.get("type") as TabKey) || "ALL";

  const [activeTab, setActiveTab] = useState<TabKey>(initialType);
  const [searchQuery, setSearchQuery] = useState("");
  const [urgencyFilter, setUrgencyFilter] = useState<string>("ALL");
  const [artifacts, setArtifacts] = useState<IntelligenceArtifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function fetchArtifacts() {
      setLoading(true);
      setErrorNotice(null);
      try {
        const res = await listArtifacts({
          artifact_type: activeTab,
          urgency: urgencyFilter,
          search: searchQuery.trim() || undefined,
          limit: 50,
        });
        if (active) {
          setArtifacts(res.items || []);
        }
      } catch (err) {
        if (active) {
          console.error("Failed to load artifacts:", err);
          setArtifacts([]);
          setErrorNotice(err instanceof Error ? err.message : "Could not load artifacts.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    const timer = setTimeout(() => {
      void fetchArtifacts();
    }, 150);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [activeTab, searchQuery, urgencyFilter]);

  function handleArtifactUpdate(updated: IntelligenceArtifact) {
    setArtifacts((prev) =>
      prev.map((item) => (item.id === updated.id ? updated : item))
    );
  }

  // Filter items in memory if search query was typed quickly
  const displayedArtifacts = artifacts.filter((item) => {
    if (activeTab !== "ALL") {
      const type = item.artifact_type.toLowerCase();
      if (activeTab === "gap_matrix" && !type.includes("gap") && !type.includes("matrix")) return false;
      if (activeTab === "battlecard" && !type.includes("battlecard") && !type.includes("competitor")) return false;
      if (activeTab === "rail_stress" && !type.includes("rail") && !type.includes("stress")) return false;
    }
    if (urgencyFilter !== "ALL" && item.urgency !== urgencyFilter) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const titleMatch = item.title.toLowerCase().includes(q);
      const payloadStr = JSON.stringify(item.payload || {}).toLowerCase();
      return titleMatch || payloadStr.includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-8 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200">
              Interactive Decision Units
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              Live Contract Binding · Zero Mock States
            </span>
          </div>
          <h1 className="mt-2 text-2xl sm:text-3xl font-black tracking-tight text-slate-900">
            Core Intelligence Decision Units
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-slate-600 max-w-2xl">
            Interactive, non-static decision instruments: execute remediation audit actions, copy scripted commercial talk tracks, and simulate live payment rail failovers.
          </p>
        </div>

        {/* Global Instant Search Bar */}
        <div className="w-full md:w-80">
          <div className="relative">
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search bank, circular, or competitor..."
              className="w-full h-10 pl-9 pr-4 rounded-xl border border-slate-200 bg-white text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-600 focus:ring-1 focus:ring-blue-600 transition shadow-2xs font-medium"
            />
            <span className="absolute left-3 top-2.5 text-slate-400 text-xs">⌕</span>
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-2.5 text-xs text-slate-400 hover:text-slate-600"
              >
                ×
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tabs & Urgency Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Animated Sliding Pill Tabs */}
        <div className="inline-flex p-1 rounded-xl bg-slate-100 border border-slate-200 overflow-x-auto max-w-full">
          {[
            { id: "ALL", label: "All Decision Units" },
            { id: "gap_matrix", label: "Compliance Gap Matrices" },
            { id: "battlecard", label: "Competitive Battlecards" },
            { id: "rail_stress", label: "Rail Stress Monitors" },
          ].map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as TabKey)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-white text-slate-900 shadow-2xs"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Urgency Band Filters */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
            Severity:
          </span>
          {["ALL", "CRITICAL", "HIGH", "MEDIUM"].map((band) => (
            <button
              key={band}
              type="button"
              onClick={() => setUrgencyFilter(band)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition ${
                urgencyFilter === band
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {band}
            </button>
          ))}
        </div>
      </div>

      {/* Decision Units Feed */}
      {(activeTab === "ALL" || activeTab === "gap_matrix") && <EvidenceReviewer initialSignalId={searchParams.get("signal_id")} />}
      {errorNotice && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{errorNotice}</p>}
      {loading ? (
        <div className="space-y-6">
          <GapMatrixSkeleton />
          <GapMatrixSkeleton />
        </div>
      ) : displayedArtifacts.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center space-y-3 shadow-2xs">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 text-lg">
            🔍
          </div>
          <h3 className="text-base font-bold text-slate-900">
            No Decision Artifacts Found
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            {searchQuery
              ? `No artifacts match your keyword "${searchQuery}". Try searching for circular numbers like "FPR/DIR" or banks like "Providus".`
              : "No artifacts match the selected filters."}
          </p>
          <button
            type="button"
            onClick={() => {
              setActiveTab("ALL");
              setUrgencyFilter("ALL");
              setSearchQuery("");
            }}
            className="inline-flex items-center px-4 py-2 rounded-xl bg-slate-900 text-xs font-bold text-white shadow-2xs hover:bg-slate-800 transition"
          >
            Clear All Filters
          </button>
        </div>
      ) : (
        <div className="space-y-8">
          {displayedArtifacts.map((artifact) => {
            const type = (artifact.artifact_type || "").toLowerCase();

            if (type.includes("gap") || type.includes("matrix")) {
              return (
                <ComplianceGapMatrix
                  key={artifact.id}
                  artifact={artifact}
                  onUpdate={handleArtifactUpdate}
                />
              );
            }

            if (type.includes("battlecard") || type.includes("competitor")) {
              return (
                <CompetitiveBattlecard
                  key={artifact.id}
                  artifact={artifact}
                  onUpdate={handleArtifactUpdate}
                />
              );
            }

            if (type.includes("rail") || type.includes("stress")) {
              return (
                <RailStressMonitor
                  key={artifact.id}
                  artifact={artifact}
                  onUpdate={handleArtifactUpdate}
                />
              );
            }

            // Fallback render as Compliance Gap Matrix if type unspecified
            return (
              <ComplianceGapMatrix
                key={artifact.id}
                artifact={artifact}
                onUpdate={handleArtifactUpdate}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

