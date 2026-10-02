"use client";

import { useEffect, useState } from "react";
import {
  getMarketReports,
  getMarketReport,
  getMarketReportStatus,
  generateMarketReport,
} from "@/lib/market-reports";
import type {
  MarketReportRecord,
  MarketReportPayload,
  MarketPlayer,
} from "@/lib/types";

const PRESET_SECTORS = [
  {
    slug: "cross-border-fx",
    title: "B2B Cross-Border & FX Settlement",
    desc: "Cross-border payment corridors, IMTO remittance rails, FX spreads, and international trade settlement.",
    regulators: ["CBN", "SEC", "NFIU"],
    badge: "Trade & Corridors",
  },
  {
    slug: "virtual-accounts",
    title: "Virtual Account Issuance & Collections",
    desc: "Dynamic virtual account generation, merchant checkout acquiring, BaaS partner banks, and collection webhooks.",
    regulators: ["CBN", "NIBSS"],
    badge: "BaaS & Acquiring",
  },
  {
    slug: "agency-banking",
    title: "POS Agency Banking & Cash-In/Cash-Out",
    desc: "Last-mile cash distribution, POS terminal acquiring networks, SANEF agent compliance, and interchange economics.",
    regulators: ["CBN", "SANEF", "NIBSS"],
    badge: "Agency & CICO",
  },
  {
    slug: "digital-lending",
    title: "Digital Lending & Credit Infrastructure",
    desc: "Consumer and SME digital lending, credit scoring APIs, FCCPC lending regulations, and default recovery rails.",
    regulators: ["CBN", "FCCPC", "NDPC"],
    badge: "Credit & Lending",
  },
];

export function MarketReportsExplorer() {
  const [sectors, setSectors] = useState<MarketReportRecord[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [activeReport, setActiveReport] = useState<MarketReportRecord | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);

  // Load available reports catalog
  useEffect(() => {
    let active = true;
    async function loadCatalog() {
      try {
        const res = await getMarketReports();
        if (active) {
          setSectors(res.items || []);
        }
      } catch (err) {
        if (active) {
          setErrorNotice(
            err instanceof Error ? err.message : "Failed to load market reports catalog."
          );
        }
      } finally {
        if (active) setLoadingList(false);
      }
    }
    void loadCatalog();
    return () => {
      active = false;
    };
  }, []);

  // Load selected report details
  useEffect(() => {
    if (!selectedSlug) return;

    const currentSlug = selectedSlug;
    let active = true;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    async function fetchReport() {
      try {
        const res = await getMarketReport(currentSlug, true);
        if (!active) return;

        if (res.report_payload) {
          setActiveReport(res);
          setSectors((prev) =>
            prev.map((item) => (item.sector_slug === res.sector_slug ? res : item))
          );
          setLoadingReport(false);
          return;
        }

        // Response indicated synthesis is in progress: start polling status
        pollTimer = setInterval(async () => {
          if (!active) {
            if (pollTimer) clearInterval(pollTimer);
            return;
          }
          try {
            const statusRes = await getMarketReportStatus(currentSlug);
            if (statusRes.status === "completed") {
              if (pollTimer) clearInterval(pollTimer);
              const completedReport = statusRes.report || await getMarketReport(currentSlug, false);
              if (active) {
                setActiveReport(completedReport);
                setSectors((prev) =>
                  prev.map((item) => (item.sector_slug === completedReport.sector_slug ? completedReport : item))
                );
                setLoadingReport(false);
              }
            } else if (statusRes.status === "failed") {
              if (pollTimer) clearInterval(pollTimer);
              if (active) {
                setErrorNotice(statusRes.error || "Market report synthesis encountered an error.");
                setLoadingReport(false);
              }
            }
          } catch {
            // Keep polling until success or component unmount
          }
        }, 3000);
      } catch (err) {
        if (active) {
          setErrorNotice(
            err instanceof Error ? err.message : "Failed to load report for this sector."
          );
          setLoadingReport(false);
        }
      }
    }

    void fetchReport();
    return () => {
      active = false;
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [selectedSlug]);

  function selectSector(slug: string | null) {
    setSelectedSlug(slug);
    setActiveReport(null);
    setLoadingReport(Boolean(slug));
    setErrorNotice(null);
  }

  async function handleRefresh(slug: string) {
    setGenerating(true);
    setErrorNotice(null);
    try {
      await generateMarketReport(slug);
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts += 1;
        try {
          const statusRes = await getMarketReportStatus(slug);
          if (statusRes.status === "completed") {
            clearInterval(interval);
            const updated = statusRes.report || await getMarketReport(slug, false);
            setActiveReport(updated);
            setSectors((prev) =>
              prev.map((item) => (item.sector_slug === slug ? updated : item))
            );
            setGenerating(false);
          } else if (statusRes.status === "failed") {
            clearInterval(interval);
            setErrorNotice(statusRes.error || "Failed to refresh market report.");
            setGenerating(false);
          } else if (attempts >= 40) {
            clearInterval(interval);
            setErrorNotice("Report generation is taking longer than expected. Please check back shortly.");
            setGenerating(false);
          }
        } catch {
          if (attempts >= 40) {
            clearInterval(interval);
            setGenerating(false);
          }
        }
      }, 3000);
    } catch (err) {
      setErrorNotice(
        err instanceof Error ? err.message : "Failed to refresh market report."
      );
      setGenerating(false);
    }
  }

  async function handlePrintPdf() {
    if (!activeReport?.report_payload) return;
    try {
      const { accessToken: getToken } = await import("@/lib/api");
      const payload = activeReport.report_payload;
      const response = await fetch("/api/v1/workspace/export", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
        },
        body: JSON.stringify({
          format: "pdf",
          title: payload.vertical_name || activeReport.sector_title || "Market Intelligence Report",
          operational_exposure: `Market Architecture: ${payload.vertical_name || activeReport.sector_title}\n\nCommercial Economics:\n${payload.commercial_economics}\n\nStrategic Outlook:\n${payload.strategic_outlook}`,
          context_and_precedents: payload.regulatory_headwinds.join("\n"),
          role_action_items: [],
          citations: [],
        }),
      });
      if (!response.ok) throw new Error("PDF generation failed");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `stem-market-report-${selectedSlug}-${Date.now()}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF export failed:", err);
      setErrorNotice("PDF export failed. Please try again.");
    }
  }

  return (
    <div className="space-y-6">
      {loadingList ? (
        <div className="grid gap-5 md:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-52 rounded-2xl border border-slate-200 bg-slate-100 animate-pulse" />
          ))}
        </div>
      ) : errorNotice && !selectedSlug ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-semibold text-red-800"
        >
          {errorNotice}
        </div>
      ) : !selectedSlug ? (
        <div className="space-y-6">
          <div className="border-b border-slate-200 pb-4">
            <h2 className="text-xl font-bold text-slate-900">
              African Fintech Vertical Intelligence Reports
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              CB Insights-style market architecture reports synthesized from historical regulatory signals,
              verified clearing rail dossiers, and live market intelligence.
            </p>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            {PRESET_SECTORS.map((preset) => {
              const record = sectors.find((s) => s.sector_slug === preset.slug);
              const isGenerated = Boolean(record?.report_payload);
              const entitiesCount = record?.monitored_entities_count || 0;

              return (
                <div
                  key={preset.slug}
                  className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-6 shadow-2xs transition hover:border-slate-300 hover:shadow-xs"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-blue-700 border border-blue-200">
                        {preset.badge}
                      </span>
                      {isGenerated ? (
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-700">
                          <span className="h-2 w-2 rounded-full bg-emerald-500" />
                          {entitiesCount} Reported Operators
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-amber-700">
                          <span className="h-2 w-2 rounded-full bg-amber-400" />
                          Available to Synthesize
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-bold text-slate-900">
                      {preset.title}
                    </h3>
                    <p className="text-xs text-slate-600 leading-relaxed">
                      {preset.desc}
                    </p>

                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                        Regulators:
                      </span>
                      {preset.regulators.map((reg) => (
                        <span
                          key={reg}
                          className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-700"
                        >
                          {reg}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4">
                    <span className="text-[11px] font-mono text-slate-400">
                      {record?.last_generated_at
                        ? `Last updated ${new Date(record.last_generated_at).toLocaleDateString()}`
                        : "Ready on demand"}
                    </span>
                    <button
                      type="button"
                      onClick={() => selectSector(preset.slug)}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-4 py-2 text-xs font-bold text-white shadow-2xs hover:bg-slate-800 transition"
                    >
                      <span>View Intelligence Report</span>
                      <span>→</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* Detailed Report View */
        <div className="space-y-6">
          {/* Action Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4 print:hidden">
            <button
              type="button"
              onClick={() => selectSector(null)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition"
            >
              ← Back to Sector Grid
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => selectedSlug && void handleRefresh(selectedSlug)}
                disabled={generating || loadingReport}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-800 shadow-2xs hover:bg-slate-50 disabled:opacity-40 transition"
              >
                {generating ? "Synthesizing…" : "Refresh Intelligence"}
              </button>
              <button
                type="button"
                onClick={handlePrintPdf}
                disabled={loadingReport || !activeReport?.report_payload}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-2xs hover:bg-blue-700 disabled:opacity-40 transition"
              >
                <span>Export Executive PDF</span>
                <span>🖨️</span>
              </button>
            </div>
          </div>

          {loadingReport ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center space-y-4">
              <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-slate-900 border-t-transparent" />
              <h3 className="text-sm font-bold text-slate-900">
                Synthesizing Vertical Market Architecture…
              </h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Aggregating historical regulatory signals, clearing rail profiles, and conducting dynamic verification.
              </p>
            </div>
          ) : activeReport?.report_payload ? (
            <ReportContent
              record={activeReport}
              payload={activeReport.report_payload}
            />
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center space-y-3">
              <h3 className="text-base font-bold text-slate-900">
                No Report Data Available
              </h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Could not retrieve or synthesize report data for this sector.
              </p>
              <button
                type="button"
                onClick={() => selectedSlug && void handleRefresh(selectedSlug)}
                className="rounded-xl bg-slate-900 px-4 py-2 text-xs font-bold text-white shadow-2xs hover:bg-slate-800"
              >
                Generate Report
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ReportContent({
  record,
  payload,
}: {
  record: MarketReportRecord;
  payload: MarketReportPayload;
}) {
  const leaders = payload.players.filter((p) => p.category.toLowerCase().includes("leader"));
  const challengers = payload.players.filter((p) => p.category.toLowerCase().includes("challenger"));
  const niche = payload.players.filter(
    (p) =>
      !p.category.toLowerCase().includes("leader") &&
      !p.category.toLowerCase().includes("challenger")
  );

  // Collect unique rails across all players
  const allRails = Array.from(
    new Set(payload.players.flatMap((p) => p.known_rails || []))
  ).filter(Boolean);

  return (
    <article className="space-y-8 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-xs print:border-none print:shadow-none print:p-0">
      {/* Executive Report Header */}
      <header className="border-b border-slate-200 pb-6 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider text-blue-700 border border-blue-200">
              Market Intelligence & Architecture
            </span>
            <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
              {record.primary_jurisdiction || "Nigeria"}
            </span>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {record.last_generated_at
              ? `Report Published: ${new Date(record.last_generated_at).toLocaleString()}`
              : "Live Synthesis"}
          </span>
        </div>

        <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900">
          {payload.vertical_name || record.sector_title}
        </h1>

        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Primary Regulators:
          </span>
          {payload.primary_regulators.map((reg) => (
            <span
              key={reg}
              className="rounded-md bg-slate-900 px-2.5 py-0.5 text-xs font-bold text-white"
            >
              {reg}
            </span>
          ))}
          <span className="ml-2 text-xs font-medium text-slate-500">
            ({payload.players.length} Operators Included)
          </span>
        </div>
      </header>

      {/* 1. Market Map & Players (CB Insights 3-Tier Categorization) */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 uppercase tracking-wider">
            1. Market Map & Competitive Architecture
          </h2>
          <span className="text-xs text-slate-500 font-medium">
            3-Tier Standing: Leaders · Challengers · Niche Specialists
          </span>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Leaders Column */}
          <div className="space-y-3 rounded-xl border border-blue-200 bg-blue-50/40 p-4">
            <div className="flex items-center justify-between border-b border-blue-200 pb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-900 flex items-center gap-1.5">
                <span>🏆</span>
                <span>Market Leaders</span>
              </span>
              <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-bold text-blue-800">
                {leaders.length}
              </span>
            </div>
            {leaders.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">
                No dominant leader established in available evidence.
              </p>
            ) : (
              leaders.map((p) => <PlayerCard key={p.name} player={p} tier="leader" />)
            )}
          </div>

          {/* Challengers Column */}
          <div className="space-y-3 rounded-xl border border-amber-200 bg-amber-50/30 p-4">
            <div className="flex items-center justify-between border-b border-amber-200 pb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-900 flex items-center gap-1.5">
                <span>⚡</span>
                <span>Emerging Challengers</span>
              </span>
              <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-800">
                {challengers.length}
              </span>
            </div>
            {challengers.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">
                No challengers mapped in this cohort.
              </p>
            ) : (
              challengers.map((p) => <PlayerCard key={p.name} player={p} tier="challenger" />)
            )}
          </div>

          {/* Niche Specialists Column */}
          <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/60 p-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                <span>🎯</span>
                <span>Niche Specialists</span>
              </span>
              <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-bold text-slate-800">
                {niche.length}
              </span>
            </div>
            {niche.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">
                No niche operators identified.
              </p>
            ) : (
              niche.map((p) => <PlayerCard key={p.name} player={p} tier="niche" />)
            )}
          </div>
        </div>
      </section>

      {/* 2. Infrastructure & Rail Footprint */}
      <section className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/50 p-5">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
          2. Clearing Switches & Partner Settlement Rails
        </h2>
        <p className="text-xs text-slate-600">
          Underlying transaction switches and commercial clearing bank counterparties powering this vertical.
        </p>

        <div className="flex flex-wrap gap-2 pt-2">
          {allRails.map((rail) => (
            <span
              key={rail}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-800 shadow-2xs"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-blue-600" />
              {rail}
            </span>
          ))}
          {allRails.length === 0 && (
            <p className="text-xs text-slate-500 italic">
              Rail dependencies not explicitly parsed in current dossier evidence.
            </p>
          )}
        </div>
      </section>

      {/* 3. Commercial Economics & Margins */}
      <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
          3. Commercial Economics & Fee Benchmarks
        </h2>
        <div className="rounded-lg bg-slate-50 p-4 text-xs font-medium leading-relaxed text-slate-800 whitespace-pre-line border border-slate-200/60">
          {payload.commercial_economics}
        </div>
      </section>

      {/* 4. Regulatory Headwinds */}
      <section className="space-y-3 rounded-xl border border-red-200/80 bg-red-50/30 p-5">
        <h2 className="text-sm font-bold text-red-900 uppercase tracking-wider flex items-center gap-2">
          <span>⚠️</span>
          <span>4. Regulatory Headwinds & Active Circulars</span>
        </h2>
        <ul className="space-y-2 pt-1">
          {payload.regulatory_headwinds.map((item, idx) => (
            <li
              key={idx}
              className="flex items-start gap-2.5 rounded-lg border border-red-100 bg-white p-3 text-xs text-slate-800 shadow-2xs"
            >
              <span className="mt-0.5 text-red-600 font-bold">§</span>
              <span className="leading-relaxed">{item}</span>
            </li>
          ))}
          {payload.regulatory_headwinds.length === 0 && (
            <li className="text-xs text-slate-500 italic">
              No active circular headwinds reported for this period.
            </li>
          )}
        </ul>
      </section>

      {/* 5. Strategic Outlook (6-12 Months) */}
      <section className="space-y-3 rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50/50 to-indigo-50/40 p-5">
        <h2 className="text-sm font-bold text-blue-900 uppercase tracking-wider flex items-center gap-2">
          <span>🔮</span>
          <span>5. Strategic Outlook (6–12 Month Horizon)</span>
        </h2>
        <div className="rounded-lg bg-white/90 p-4 text-xs font-medium leading-relaxed text-slate-800 whitespace-pre-line border border-blue-100 shadow-2xs">
          {payload.strategic_outlook}
        </div>
      </section>

      {/* Report Footer / Provenance */}
      <footer className="border-t border-slate-200 pt-4 flex flex-wrap items-center justify-between text-[11px] text-slate-400">
        <span>Stem Cogent Vertical Intelligence Engine · CB Insights-Grade Taxonomy</span>
        <span>AI-generated analysis; review the underlying evidence before acting</span>
      </footer>
    </article>
  );
}

function PlayerCard({
  player,
  tier,
}: {
  player: MarketPlayer;
  tier: "leader" | "challenger" | "niche";
}) {
  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-3.5 shadow-2xs">
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-bold text-slate-900">{player.name}</h4>
        <span
          className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
            tier === "leader"
              ? "bg-blue-100 text-blue-800"
              : tier === "challenger"
              ? "bg-amber-100 text-amber-800"
              : "bg-slate-100 text-slate-700"
          }`}
        >
          {player.category}
        </span>
      </div>

      <p className="text-xs text-slate-600 leading-snug">
        {player.core_offering}
      </p>

      <div className="space-y-1.5 pt-1 border-t border-slate-100">
        <div className="text-[11px]">
          <span className="font-semibold text-slate-500">Charter/Moat: </span>
          <span className="font-medium text-slate-800">{player.licensing_moat}</span>
        </div>

        {player.known_rails && player.known_rails.length > 0 && (
          <div className="flex flex-wrap items-center gap-1 pt-0.5">
            <span className="text-[10px] font-semibold text-slate-400">Rails:</span>
            {player.known_rails.map((rail) => (
              <span
                key={rail}
                className="rounded bg-slate-100 px-1.5 py-0.5 text-[9px] font-medium text-slate-700"
              >
                {rail}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
