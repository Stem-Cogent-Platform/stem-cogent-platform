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
  brief_contract?: DecisionBriefContract;
};

export type DecisionBriefContract = {
  decision: string;
  why_now: string;
  what_changed: string;
  exposure: string;
  exposure_types: string[];
  stakes: string;
  stakes_types: string[];
  decision_paths: DecisionPath[];
  trade_offs: string[];
  validate_next: string[];
  unknowns: string[];
  owner: string;
  timing: string;
  evidence: Evidence[];
  source_metrics: Record<string, unknown>;
  entry_prompt: string;
  suggested_inquiries: string[];
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

export type Severity = "low" | "moderate" | "high" | "critical";
export type Urgency = "monitor" | "this_quarter" | "this_month" | "this_week" | "immediate";

export type MultiDimensionalImpact = {
  financial_margin: Severity;
  regulatory_licensing: Severity;
  operational_liquidity: Severity;
  customer_experience: Severity;
  summary_of_consequence: string;
};

export type ActionItem = {
  id?: string;
  action_id?: string;
  function?: string;
  accountable_role?: string;
  action: string;
  urgency?: Urgency;
  deadline?: string | null;
  completed?: boolean;
  completed_at?: string | null;
  notes?: string;
};

export type ComplianceGapPayload = {
  regulatory_body: string;
  circular_reference: string;
  statutory_mandate: string;
  current_internal_baseline: string;
  identified_gap: string;
  severity: Severity;
  urgency: Urgency;
  impact?: MultiDimensionalImpact;
  statutory_fine_exposure?: string | null;
  statutory_fine_daily_naira?: number;
  statutory_deadline?: string | null;
  corrective_actions?: ActionItem[];
  action_plan?: ActionItem[];
  remediation_state?: Record<string, { completed: boolean; completed_at?: string | null; notes?: string }>;
  [key: string]: unknown;
};

export type StrategicOption = {
  posture: "counter_attack" | "monitor_and_observe" | "accelerate_internal_roadmap" | "deliberately_ignore" | string;
  strategic_rationale: string;
  trade_off: string;
};

export type CompetitorStrategicPayload = {
  competitor_name: string;
  event_classification?: string;
  verified_move: string;
  commercial_implication: string;
  vulnerable_segments?: string[];
  impact?: MultiDimensionalImpact;
  options?: StrategicOption[];
  commercial_talk_track?: string | null;
  attack_defense?: {
    strengths?: string[];
    vulnerabilities?: string[];
    objection_talk_tracks?: Array<{
      id: string;
      buyer_objection: string;
      scripted_response: string;
      landmine_question?: string;
      target_channel?: string;
    }>;
  };
  licensing_charters?: {
    licensing_status?: string;
    regulatory_exposure?: string;
    sponsor_bank_dependencies?: string[];
  };
  margin_pricing?: {
    pricing_model?: string;
    take_rate_estimate?: string;
    margin_squeeze_analysis?: string;
    counter_pricing_strategy?: string;
  };
  trap_setting_moves?: Array<{
    id: string;
    verified_fact: string;
    margin_squeeze_calculation: string;
    counter_move: string;
  }>;
  executive_stance?: {
    stance: "counter_attack" | "monitor" | "ignore";
    rationale?: string | null;
    updated_at?: string;
    updated_by?: string;
  };
  [key: string]: unknown;
};

export type RailDegradationPayload = {
  impacted_node: string;
  affected_rail_channel?: string;
  telemetry_trigger: string;
  operational_exposure: string;
  severity: Severity;
  urgency: Urgency;
  impact?: MultiDimensionalImpact;
  recommended_fallback_node?: string | null;
  immediate_mitigation_actions?: ActionItem[];
  latency_ms?: number;
  latency_baseline_ms?: number;
  success_rate_pct?: number;
  settlement_queue_depth?: number;
  at_risk_volume_naira?: number;
  merchant_notice_template?: {
    headline: string;
    banner_text: string;
    technical_details?: string;
    eta?: string;
  };
  [key: string]: unknown;
};

export type IntelligenceArtifact = {
  id: string;
  tenant_id: string;
  signal_id: string;
  artifact_type: "compliance_gap_matrix" | "compliance_gap" | "competitor_strategic_battlecard" | "competitive_battlecard" | "rail_degradation_stress_index" | "rail_stress" | string;
  title: string;
  urgency: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  payload: (Partial<ComplianceGapPayload> & Partial<CompetitorStrategicPayload> & Partial<RailDegradationPayload> & Record<string, any>);
  is_dismissed: boolean;
  created_at: string;
  updated_at: string;
};

export type ArtifactListResponse = {
  items: IntelligenceArtifact[];
  total: number;
  limit: number;
  offset: number;
};

export type FailoverSimulationResult = {
  timestamp: string;
  target_node: string;
  traffic_rerouted_pct: number;
  latency_baseline_ms: number;
  latency_recovered_ms: number;
  latency_reduction_pct: number;
  at_risk_volume_protected_naira: number;
  node_health_status: string;
  routing_steps: Array<{
    step: number;
    action: string;
    status: string;
    latency_ms?: number;
    traffic_shifted_pct?: number;
    success_rate_pct?: number;
  }>;
};

export type WorkspaceSession = {
  id: string;
  organization_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type WebSearchResultItem = {
  title: string;
  url: string;
  text: string;
  published_date?: string | null;
};

export type DepartmentActionItem = {
  department: string;
  action: string;
  urgency: "immediate" | "this_week" | "this_month" | "monitor" | string;
};

export type ExecutiveSynthesisPayload = {
  operational_exposure: string;
  context_and_precedents: string;
  role_action_items: DepartmentActionItem[];
  cited_artifact_ids: string[];
  web_sources: WebSearchResultItem[];
};

export type WorkspaceMessage = {
  id: string;
  session_id: string;
  organization_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  tool_provenance?: Record<string, unknown> | null;
  cited_artifact_ids?: string[] | null;
  created_at: string;
};

export type WorkspaceTurnResponse = {
  competitive_research?: import("./competitors").ResearchResult | null;
  session_id: string;
  user_message: WorkspaceMessage;
  assistant_message: WorkspaceMessage;
  synthesis: ExecutiveSynthesisPayload;
};

export type OnboardingStatus = {
  organization_id: string;
  organization_name: string;
  subscription_tier: string;
  pilot_days_remaining: number | null;
  monthly_workspace_query_limit: number;
  queries_used_this_period: number;
  stage_a_completed: boolean;
  stage_b_completed: boolean;
  business_function?: string | null;
  decision_lens?: string | null;
  priority_focus?: string | null;
  is_superuser: boolean;
};

export type TelemetryData = {
  status: string;
  total_verified_signals: number;
  latest_signal_at: string | null;
  signals_by_type?: Record<string, number>;
  feeds_active: number;
  nodes?: Array<{
    name: string;
    status: "OPTIMAL" | "OPERATIONAL" | "DEGRADED" | "OUTAGE";
    latency_ms: number;
    success_rate_pct: number;
    volume_at_risk_naira?: number;
  }>;
};

export type AdminTenant = {
  organization_id: string;
  name: string;
  subscription_tier: string;
  trial_days_remaining: number | null;
  monthly_workspace_query_limit: number;
  queries_used_this_period: number;
  stage_a_completed: boolean;
  seat_count: number;
  created_at: string | null;
};

