"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

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

export interface IntelligenceTabMeta {
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

export default function IntelligencePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/artifacts");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-500 text-xs font-mono">
      Transitioning to Decision Artifacts...
    </div>
  );
}
