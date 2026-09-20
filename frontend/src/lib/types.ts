export type Brief = {
  id: string;
  what_changed: string;
  why_it_matters?: string;
  exposure_summary?: string;
  stakes_summary?: string;
  decision_prompt?: string;
  owner_roles: string[];
  uncertainties: string[];
  matched_company_objects?: string[];
  evidence_signal_ids: string[];
  brief_status: string;
  personal_priority_score?: number;
  relevance_band: string;
  relevance_score: number;
  quantification_status: string;
  primary_domain?: string;
  urgency_band?: string;
  confidence_band?: string;
  created_at: string;
  decision_window?: string;
  first_published_at?: string;
  last_material_change_at?: string;
  material_change_count?: number;
  published_at?: string;
  detected_at?: string;
  exposure_types?: string[];
  stakes_types?: string[];
  gaps_summary?: string;
  response_options?: DecisionPath[];
  next_validation_steps?: string[];
  guidance_status?: string;
  timeline?: BriefTimelineEvent[];
  evidence?: Evidence[];
  source_metrics?: SourceMetrics;
  actions?: DecisionAction[];
};

export type SourceMetrics = {
  source_count: number;
  independent_source_count: number;
  primary_source_count: number;
  corroboration_strength: string;
};

export type DecisionPath = {
  option_code: string;
  title: string;
  description: string;
  tradeoffs?: string[];
  evidence_signal_ids?: string[];
};

export type BriefTimelineEvent = {
  event_type: string;
  event_metadata?: Record<string, unknown>;
  created_at: string;
};

export type Evidence = {
  id: string;
  title?: string;
  source_url?: string;
  canonical_url?: string;
  source_name: string;
  published_at?: string;
  detected_at?: string;
  confidence_band?: string;
  is_primary?: boolean;
  duplicate_count?: number;
  freshness?: string;
  effective_at?: string;
};

export type DecisionAction = {
  id: string;
  action_type: string;
  note?: string;
  created_at: string;
  display_name?: string;
};

export type LoadState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };
