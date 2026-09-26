import { apiRequest } from "./api";

export type Citation = {source_id: string; excerpt: string};
export type Claim = {value: string; citations: Citation[]};
export type EvidenceSource = {id: string; kind: string; title: string; text: string; url: string | null};
export type Comparison = {point: string; detail: string; citations: Citation[]};
export type Dossier = {
  id: string; competitor_name: string; canonical_domain: string | null;
  processing_status: string; error_code: string | null; last_refreshed_at: string | null;
  known_licenses: string[]; primary_settlement_rails: string[]; core_target_segments: string[];
  fee_model_summary: string | null; strengths_vs_us: Comparison[]; weaknesses_vs_us: Comparison[];
  profile: {known_licenses?: Claim[]; primary_settlement_rails?: Claim[]; core_target_segments?: Claim[]; fee_model?: Claim | null; unknowns?: string[]};
  evidence: EvidenceSource[]; provenance: {live_search_available?: boolean};
  battlecards?: Array<{id: string; title: string; urgency: string}>;
};
export type NoteFinding = {point: string; theme: string; excerpt: string};
export type DealSignal = {
  id: string; competitor_id: string; competitor_name_raw: string; deal_outcome: "won" | "lost" | "churned";
  merchant_segment: string; deal_size_arr_or_gmv: string | null; occurred_on: string; processing_status: string;
  error_code: string | null; extracted_decision_drivers: string[]; objections_encountered: string[];
  winning_talk_track: string | null; talk_track_kind: "observed" | "suggested" | "unknown";
  raw_sales_notes?: string; extraction: {decision_drivers?: NoteFinding[]; objections_encountered?: NoteFinding[]; limitations?: string[]};
};
export type Insights = {
  metrics: {reported: number; analyzed: number; won: number; lost: number; churned: number; pending: number; failed: number; win_rate: number | null; win_rate_denominator: number};
  themes: Array<{theme: string; deal_outcome: string; count: number}>;
  recent_signals: DealSignal[];
  objections: Array<{objection: string; count: number; source_ids: string[]}>;
  metric_definition: string;
  filters: {competitor_name?: string | null; merchant_segment?: string | null; start_date?: string | null; end_date?: string | null};
};
export type ResearchResult = Insights & {
  status: string; scope_notes: string[]; sources: EvidenceSource[];
  playbook: {findings: Claim[]; recommended_actions: Claim[]; limitations: string[]};
};

export const getDossiers = () => apiRequest<{items: Dossier[]}>("/api/v1/competitors/dossiers");
export const getDossier = (id: string) => apiRequest<Dossier>(`/api/v1/competitors/dossiers/${id}`);
export const generateDossier = (competitor_name: string, refresh = false) => apiRequest<Dossier>("/api/v1/competitors/dossiers/generate", {method: "POST", body: JSON.stringify({competitor_name, refresh})});
export const getDeal = (id: string) => apiRequest<DealSignal>(`/api/v1/competitors/deal-signals/${id}`);
export const retryDeal = (id: string) => apiRequest<DealSignal>(`/api/v1/competitors/deal-signals/${id}/retry`, {method: "POST"});
export const getInsights = (filters: Record<string, string> = {}) => apiRequest<Insights>(`/api/v1/competitors/win-loss-insights?${new URLSearchParams(Object.entries(filters).filter(([, value]) => value))}`);
