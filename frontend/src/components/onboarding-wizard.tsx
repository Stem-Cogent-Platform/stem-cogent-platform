// Deprecated: Onboarding wizard superseded by Two-Stage Onboarding (/onboarding/stage-a and /onboarding/stage-b)
// Retained as compatibility module for audit traceability.
export const alertThresholds = ["CRITICAL_ONLY", "IMPORTANT_AND_CRITICAL"];
export const digestCadences = ["DAILY", "WEEKLY"];

export async function legacyOnboardingComplete() {
  const { apiRequest } = await import("@/lib/api");
  return apiRequest("/api/v1/me/onboarding/complete", { method: "POST" });
}

export function OnboardingWizard() {
  return null;
}
