"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { CILPanel } from "@/components/cil-panel";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest, recordProductEvent } from "@/lib/api";
import { LoadState } from "@/lib/types";

export type IntelligenceTabKey =
  | "FOR_YOU"
  | "REGULATORY"
  | "COMPETITION"
  | "INFRASTRUCTURE"
  | "MARKET_CUSTOMERS"
  | "FINANCIAL_ECONOMIC"
  | "CAPITAL_PARTNERSHIPS"
  | "EXPANSION"
  | "RISK_TRUST";

interface IntelligenceTabMeta {
  key: IntelligenceTabKey;
  label: string;
  icon: string;
  description: string;
  operatorFocus: string;
}

export const INTELLIGENCE_TABS: IntelligenceTabMeta[] = [
  {
    key: "FOR_YOU",
    label: "For You",
    icon: "🎯",
    description: "Intelligence matched directly against your company dependencies, competitors, active focus areas, and Decision Lens.",
    operatorFocus: "Personalized executive stream filtering verified signals across all domains to match your specific role and business model.",
  },
  {
    key: "REGULATORY",
    label: "Regulatory",
    icon: "🏛️",
    description: "Central Bank of Nigeria (CBN) circulars, policy mandates, licensing conditions, NDIC/SEC/FCCPC supervision, and statutory compliance.",
    operatorFocus: "Licensing exposure, compliance deadlines, statutory capital requirements, and supervisory actions.",
  },
  {
    key: "COMPETITION",
    label: "Competition",
    icon: "⚔️",
    description: "Verified moves across Nigerian fintech rivals—pricing shifts, agent banking expansion, merchant acquiring, and product releases.",
    operatorFocus: "Competitor market-share defense, fee structures, merchant retention, and strategic product positioning.",
  },
  {
    key: "INFRASTRUCTURE",
    label: "Infrastructure",
    icon: "⚡",
    description: "Payment rails, NIBSS switches, USSD routing, interbank settlement latency, and core banking uptime telemetry.",
    operatorFocus: "Dispute rates, processing reliability, fallback rail switching, and operational uptime.",
  },
  {
    key: "MARKET_CUSTOMERS",
    label: "Market & Customers",
    icon: "👥",
    description: "Merchant adoption patterns, POS dispute trends, consumer wallet liquidity, and retail cash velocity shifts.",
    operatorFocus: "Volume growth, transaction churn, POS acquiring margins, and customer adoption shifts.",
  },
  {
    key: "FINANCIAL_ECONOMIC",
    label: "Financial & Economic",
    icon: "📈",
    description: "Monetary policy rate (MPR) hikes, foreign exchange volatility, card interchange yields, inflation, and treasury margin dynamics.",
    operatorFocus: "Unit economics, treasury yields, cost of float, FX exposure, and gross margin compression.",
  },
  {
    key: "CAPITAL_PARTNERSHIPS",
    label: "Capital & Partnerships",
    icon: "🤝",
    description: "Venture funding rounds, debt facilities, M&A acquisitions, strategic sponsor bank tie-ups, and ecosystem alliances.",
    operatorFocus: "Capital runway, sector valuation multiples, strategic M&A targets, and partner bank dependencies.",
  },
  {
    key: "EXPANSION",
    label: "Expansion",
    icon: "🌍",
    description: "Cross-border payment corridors (PAPSS, regional remittances), Francophone/East Africa expansion, and new licensing verticals.",
    operatorFocus: "Geographic runway, cross-border fee arbitrage, multi-currency compliance, and market entry timing.",
  },
  {
    key: "RISK_TRUST",
    label: "Risk & Trust",
    icon: "🛡️",
    description: "Emerging fraud vectors, account takeover schemes, chargeback spikes, AML/KYC enforcement actions, and cyber posture.",
    operatorFocus: "Loss mitigation, chargeback reserves, AML sanctions risk, and enterprise trust integrity.",
  },
];

type IntelligenceItem = {
  id: string;
  signal_id: string;
  title?: string;
  summary?: string;
  key_developments?: string[];
  global_implication?: string;
  primary_domain?: string;
  event_type?: string;
  urgency_band?: string;
  confidence_band?: string;
  source_name: string;
  source_url?: string;
  published_at?: string;
  detected_at?: string;
  llm_synthesis_failed?: boolean;
  freshness?: string;
  relevance_score?: number;
  relevance_band?: string;
  decision_required?: boolean;
  decision_type?: string;
  exposure_types?: string[];
  matched_company_objects?: string[];
  why_relevant?: string;
};

export default function IntelligencePage() {
  const [state, setState] = useState<LoadState<IntelligenceItem[]>>({ status: "loading" });
  const [activeTab, setActiveTab] = useState<IntelligenceTabKey>("FOR_YOU");
  const [freshness, setFreshness] = useState("CURRENT");
  const [search, setSearch] = useState("");
  const [priorityOnly, setPriorityOnly] = useState(false);
  const [investigatingSignal, setInvestigatingSignal] = useState<IntelligenceItem | null>(null);

  const activeTabMeta = INTELLIGENCE_TABS.find((t) => t.key === activeTab) ?? INTELLIGENCE_TABS[0];

  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      const queryParams = new URLSearchParams({
        freshness,
        q: search,
        tab: activeTab,
      });
      const data = await apiRequest<IntelligenceItem[]>(`/api/v1/signals?${queryParams.toString()}`);
      setState({ status: "ready", data });
      void recordProductEvent("INTELLIGENCE_VIEWED", {
        metadata: { tab: activeTab, freshness },
      });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Intelligence could not be loaded.",
      });
    }
  }, [activeTab, freshness, search]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 250);
    return () => window.clearTimeout(timer);
  }, [load]);

  const handleTabChange = (newTab: IntelligenceTabKey) => {
    setActiveTab(newTab);
    void recordProductEvent("INTELLIGENCE_TAB_CHANGED", {
      metadata: { tab: newTab },
    });
  };

  const handleInvestigate = (item: IntelligenceItem) => {
    setInvestigatingSignal(item);
  };

  const items = state.status === "ready" ? state.data : [];
  const visibleItems = items.filter(
    (item) => !priorityOnly || ["CRITICAL", "HIGH"].includes(item.urgency_band ?? "") || item.decision_required
  );

  return (
    <WorkspaceShell>
      <section className="content-page" style={{ maxWidth: investigatingSignal ? "1600px" : undefined }}>
        <div className="page-heading">
          <div>
            <p className="eyebrow">Supporting market view</p>
            <h1>Intelligence</h1>
            <p>
              Source-backed market developments across the Nigerian fintech ecosystem. Browse dedicated domain
              streams or inspect verified dossiers with bounded Cogent analyst inquiries.
            </p>
          </div>
          {state.status === "ready" && (
            <div className="page-status">
              <i></i>
              {items.length} verified developments in {activeTabMeta.label}
            </div>
          )}
        </div>

        {/* 9 Authoritative Domain Tabs */}
        <div
          className="intelligence-tabs-container"
          role="tablist"
          aria-label="Intelligence domain categories"
          style={{
            display: "flex",
            gap: "8px",
            overflowX: "auto",
            paddingBottom: "12px",
            marginBottom: "16px",
            borderBottom: "1px solid var(--border)",
            scrollbarWidth: "thin",
          }}
        >
          {INTELLIGENCE_TABS.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                role="tab"
                aria-selected={isActive}
                type="button"
                onClick={() => handleTabChange(tab.key)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "10px 16px",
                  borderRadius: "12px",
                  border: isActive ? "1px solid var(--accent)" : "1px solid var(--border)",
                  background: isActive ? "var(--accent-soft)" : "var(--bg-surface)",
                  color: isActive ? "var(--accent)" : "var(--text-secondary)",
                  fontWeight: isActive ? 700 : 500,
                  fontSize: "0.85rem",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  transition: "all 150ms ease",
                }}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Domain Stream Context Banner */}
        <div
          className="domain-stream-banner"
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "14px",
            padding: "18px 22px",
            marginBottom: "20px",
            display: "grid",
            gap: "6px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "1.3rem" }}>{activeTabMeta.icon}</span>
              <strong style={{ fontSize: "1.05rem", color: "var(--text-primary)" }}>{activeTabMeta.label} Stream</strong>
            </div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              {activeTab === "FOR_YOU" ? "Personalized Stream" : "Authoritative Domain Feed"}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
            {activeTabMeta.description}
          </p>
          <small style={{ color: "var(--accent)", fontWeight: 600, fontSize: "0.78rem" }}>
            Executive Lens: {activeTabMeta.operatorFocus}
          </small>
        </div>

        {/* Toolbar Controls */}
        <div className="intelligence-toolbar">
          <div style={{ display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.8rem", fontWeight: 600 }}>
              Time period
              <select
                aria-label="Intelligence time period"
                value={freshness}
                onChange={(event) => setFreshness(event.target.value)}
                style={{
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "6px 10px",
                  fontSize: "0.8rem",
                }}
              >
                <option value="CURRENT">Current and recent</option>
                <option value="HISTORICAL">Historical context</option>
                <option value="DATE_UNCERTAIN">Date unconfirmed</option>
                <option value="ALL">All stored intelligence</option>
              </select>
            </label>

            <label className="priority-toggle">
              <input
                checked={priorityOnly}
                onChange={(event) => setPriorityOnly(event.target.checked)}
                type="checkbox"
              />
              <span>Priority only</span>
            </label>
          </div>

          <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.8rem", fontWeight: 600, minWidth: "260px" }}>
            Search
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={`Search ${activeTabMeta.label.toLowerCase()} intelligence...`}
              maxLength={200}
              type="search"
              style={{
                flex: 1,
                background: "var(--bg-surface)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "6px 12px",
                fontSize: "0.8rem",
              }}
            />
          </label>
        </div>

        {state.status === "loading" && <ModuleLoading label={`Loading ${activeTabMeta.label} Intelligence...`} />}
        {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}

        {state.status === "ready" && (
          <div
            style={{
              display: "grid",
              gap: "24px",
              gridTemplateColumns: investigatingSignal ? "minmax(0, 1fr) 420px" : "minmax(0, 1fr)",
              alignItems: "start",
            }}
          >
            {/* Stream Cards */}
            <div className="intelligence-list">
              {visibleItems.map((item) => {
                const isInvestigatingThis = investigatingSignal?.signal_id === item.signal_id;
                return (
                  <article
                    key={item.id}
                    style={{
                      borderColor: isInvestigatingThis ? "var(--accent)" : undefined,
                      boxShadow: isInvestigatingThis ? "0 0 0 2px var(--accent-soft)" : undefined,
                    }}
                  >
                    <div
                      className="signal-accent"
                      style={{
                        background: item.decision_required
                          ? "var(--critical)"
                          : item.urgency_band === "CRITICAL"
                          ? "var(--critical)"
                          : item.urgency_band === "HIGH"
                          ? "var(--high)"
                          : undefined,
                      }}
                    />

                    {/* Metadata Badges */}
                    <div className="brief-meta" style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}>
                      {item.decision_required && (
                        <span className="priority-chip priority-critical" style={{ fontWeight: 700 }}>
                          ⚡ DECISION REQUIRED
                        </span>
                      )}
                      <span className={`priority-chip priority-${(item.urgency_band ?? "standard").toLowerCase()}`}>
                        {item.urgency_band ?? "MONITOR"}
                      </span>
                      {item.primary_domain && (
                        <span style={{ fontWeight: 600 }}>{item.primary_domain.replaceAll("_", " ")}</span>
                      )}
                      {item.event_type && (
                        <span style={{ color: "var(--text-secondary)" }}>{item.event_type.replaceAll("_", " ")}</span>
                      )}
                      <span>
                        {item.freshness === "HISTORICAL"
                          ? "Historical context"
                          : item.freshness === "DATE_UNCERTAIN"
                          ? "Publication date unconfirmed"
                          : item.freshness?.toLowerCase()}
                      </span>
                      <span>{item.confidence_band?.replaceAll("_", " ").toLowerCase() || "Unassessed"} confidence</span>
                      {item.llm_synthesis_failed && <span>Analysis unavailable</span>}
                    </div>

                    {/* Title */}
                    <h2>
                      <Link href={`/signals/${item.signal_id}`} prefetch={false}>
                        {item.title || item.summary}
                      </Link>
                    </h2>

                    {/* Matched Company Objects & Relevance */}
                    {item.matched_company_objects && item.matched_company_objects.length > 0 && (
                      <div
                        style={{
                          background: "var(--accent-soft)",
                          border: "1px solid #dbe0ff",
                          borderRadius: "8px",
                          padding: "8px 12px",
                          marginBottom: "12px",
                          fontSize: "0.82rem",
                          color: "var(--accent)",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          flexWrap: "wrap",
                        }}
                      >
                        <strong>🎯 Relevant to:</strong>
                        <span>{item.matched_company_objects.join(" · ")}</span>
                      </div>
                    )}

                    {/* Executive Relevance Rationale */}
                    {item.why_relevant && (
                      <p
                        style={{
                          fontSize: "0.86rem",
                          color: "var(--text-primary)",
                          background: "var(--bg-subtle)",
                          padding: "10px 14px",
                          borderRadius: "8px",
                          lineHeight: 1.5,
                          marginBottom: "12px",
                        }}
                      >
                        <strong style={{ display: "block", fontSize: "0.76rem", textTransform: "uppercase", color: "var(--text-secondary)", marginBottom: "4px" }}>
                          Executive Relevance
                        </strong>
                        {item.why_relevant}
                      </p>
                    )}

                    {/* Summary / Implication */}
                    <p>
                      {item.llm_synthesis_failed
                        ? "Source evidence retained. Open the dossier to review what is known and what remains unassessed."
                        : item.global_implication || item.summary}
                    </p>

                    <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                      {item.published_at ? `Published ${new Date(item.published_at).toLocaleDateString()}` : "Publication date unavailable"}
                      {item.detected_at ? ` · Detected ${new Date(item.detected_at).toLocaleDateString()}` : ""}
                    </p>

                    <footer>
                      <span>
                        <b>Source</b>
                        {item.source_name}
                      </span>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                        {item.source_url && (
                          <a href={item.source_url} rel="noreferrer" target="_blank" style={{ fontSize: "0.75rem", color: "var(--link)" }}>
                            Open source ↗
                          </a>
                        )}
                        <button
                          type="button"
                          onClick={() => handleInvestigate(item)}
                          style={{
                            background: isInvestigatingThis ? "var(--accent)" : "var(--accent-soft)",
                            color: isInvestigatingThis ? "#ffffff" : "var(--accent)",
                            border: "1px solid var(--accent)",
                            borderRadius: "8px",
                            padding: "6px 12px",
                            fontSize: "0.78rem",
                            fontWeight: 600,
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                          }}
                        >
                          🔍 {isInvestigatingThis ? "Investigating..." : "Investigate with Cogent"}
                        </button>
                        <Link href={`/signals/${item.signal_id}`} prefetch={false} style={{ fontWeight: 650, fontSize: "0.78rem" }}>
                          View dossier →
                        </Link>
                      </div>
                    </footer>
                  </article>
                );
              })}

              {!visibleItems.length && (
                <section className="empty-brief">
                  <h2>
                    {items.length
                      ? "No intelligence matches these filters."
                      : freshness === "CURRENT"
                      ? `No verified recent intelligence in ${activeTabMeta.label}.`
                      : `No stored intelligence in ${activeTabMeta.label}.`}
                  </h2>
                  <p>
                    {items.length
                      ? "Choose another time period or uncheck priority-only."
                      : `Stem is monitoring ${activeTabMeta.label.toLowerCase()} developments. Verified market developments will appear here when corroborated.`}
                  </p>
                </section>
              )}
            </div>

            {/* Slide-over / Side-by-side Cogent Analyst Panel */}
            {investigatingSignal && (
              <aside
                style={{
                  position: "sticky",
                  top: "84px",
                  maxHeight: "calc(100vh - 100px)",
                  display: "grid",
                  gridTemplateRows: "auto minmax(0, 1fr)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    background: "var(--bg-surface)",
                    border: "1px solid var(--border)",
                    borderBottom: "0",
                    borderRadius: "14px 14px 0 0",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span>🔍</span>
                    <strong style={{ fontSize: "0.85rem" }}>Investigating with Cogent</strong>
                  </div>
                  <button
                    type="button"
                    onClick={() => setInvestigatingSignal(null)}
                    style={{
                      background: "transparent",
                      border: "0",
                      cursor: "pointer",
                      fontSize: "1.1rem",
                      color: "var(--text-secondary)",
                    }}
                    aria-label="Close analyst panel"
                  >
                    ✕
                  </button>
                </div>
                <CILPanel
                  anchorId={investigatingSignal.signal_id}
                  anchorType="SIGNAL"
                  initialPrompt={`What does this mean for our business, and what should we monitor or investigate regarding: "${investigatingSignal.title || investigatingSignal.summary}"?`}
                  suggestedInquiries={[
                    `What are the direct regulatory and compliance implications?`,
                    `How does this affect our competitors and market position?`,
                    `What are the operational and transaction risks for us?`,
                  ]}
                />
              </aside>
            )}
          </div>
        )}
      </section>
    </WorkspaceShell>
  );
}
