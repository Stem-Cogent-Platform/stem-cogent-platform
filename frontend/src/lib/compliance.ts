import { apiRequest } from "./api";

export type GapStatus = "adequately_met" | "partially_met" | "gap_deficient";
export const statusLabels: Record<GapStatus, string> = {
  adequately_met: "Adequately met", partially_met: "Partially met", gap_deficient: "Gap (deficient)",
};
export type Policy = {
  id: string; document_family_id: string; document_title: string; version: string;
  policy_category: string; processing_status: string; error_code: string | null;
  embedded_chunks_count: number; active: boolean; created_at: string;
};
export type PolicyList = {items: Policy[]; health: {assessed_obligations: number; policy_evidence_score: number | null}};
export type Evidence = {chunk_id: string; policy_id: string; matched_policy_title: string;
  policy_version: string; excerpt: string; similarity_score: number;
  location: {sources?: Array<{page?: number; paragraph?: number; table?: number}>}};
export type Criterion = {criterion: string; verdict: "satisfied" | "partial" | "missing" | "contradicted"; reasoning: string; evidence: Evidence[]};
export type GapAudit = {id: string; run_id: string; status: GapStatus; automated_status: GapStatus;
  revision: number; compliance_score: number; clause_reference: string; requirement_title: string;
  source_excerpt: string; source_url: string; assessment_criteria: string[];
  statutory_sanction: string | null; statutory_deadline: string | null; evidence_matches: Criterion[];
  reviewer_override: {reason: string} | null; signed_off_at: string | null};
export type AuditRun = {id: string; processing_status: string; error_code: string | null; created_at: string};
export type AuditList = {run: AuditRun | null; items: GapAudit[]};
export type ReviewEvent = {id: string; event_type: string; revision: number; reason: string; created_at: string; actor_user_id: string | null};
export type MarketingFinding = {rule_id: string; severity: string; start: number; end: number; excerpt: string;
  reason: string; source_url: string; reference: string; suggested_alternative: string};
export type MarketingResult = {id: string; findings: MarketingFinding[]; status: string; scope: string; rules_version: string; approved: boolean};

export const getPolicies = () => apiRequest<PolicyList>("/api/v1/policies");
export const getAudits = (signal: string) => apiRequest<AuditList>(`/api/v1/gap-audits?signal_id=${encodeURIComponent(signal)}`);
export const getRegulatorySignals = () => apiRequest<{items: Array<{id: string; title: string; source_url: string}>}>("/api/v1/gap-audits/signals");
export const startAudit = (signal: string) => apiRequest<AuditRun>("/api/v1/gap-audits/runs", {method: "POST", body: JSON.stringify({signal_id: signal, idempotency_key: crypto.randomUUID()})});
export const getAuditHistory = (id: string) => apiRequest<{items: ReviewEvent[]}>(`/api/v1/gap-audits/${id}/history`);
export const reviewAudit = (audit: GapAudit, action: "override" | "addendum" | "sign-off", reason: string, status?: GapStatus, policyId?: string) =>
  apiRequest<GapAudit>(`/api/v1/gap-audits/${audit.id}/${action}`, {method: action === "override" ? "PATCH" : "POST", body: JSON.stringify({reason, status: status ?? null, policy_id: policyId ?? null, expected_revision: audit.revision, idempotency_key: crypto.randomUUID()})});
export async function downloadPolicy(id: string) {
  const result = await apiRequest<{url: string}>(`/api/v1/policies/${id}/download`);
  window.open(result.url, "_blank", "noopener,noreferrer");
}
