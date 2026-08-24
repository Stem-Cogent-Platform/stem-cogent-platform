export type Brief = {
  id: string;
  what_changed: string;
  why_it_matters?: string;
  exposure_summary?: string;
  stakes_summary?: string;
  decision_prompt?: string;
  owner_roles: string[];
  uncertainties: string[];
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
  evidence?: Evidence[];
  actions?: DecisionAction[];
};

export type Evidence = {
  id: string;
  title?: string;
  source_url?: string;
  source_name: string;
  published_at?: string;
  confidence_band?: string;
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
