import { expect, Page, test } from "@playwright/test";

const user = { id: "10000000-0000-4000-8000-000000000001", workspace_id: "20000000-0000-4000-8000-000000000001", email: "pilot@example.com", display_name: "Ada Okafor", permission_role: "ADMIN", workspace_name: "Pilot Payments" };
const briefId = "30000000-0000-4000-8000-000000000001";
const brief = {
  id: briefId, what_changed: "A new settlement rule changes the implementation timeline.", why_it_matters: "Merchant settlement operations may need an implementation review.", exposure_summary: "Merchant payments and settlement operations.", stakes_summary: "Service reliability and regulatory execution.", decision_prompt: "Confirm the accountable implementation owner.", owner_roles: ["CEO", "COMPLIANCE"], decision_window: "7 days", uncertainties: ["IMPLEMENTATION_DATE"], evidence_signal_ids: ["40000000-0000-4000-8000-000000000001"], brief_status: "NEW", relevance_band: "HIGH", relevance_score: 0.88, quantification_status: "NOT_QUANTIFIED", primary_domain: "REGULATORY", urgency_band: "HIGH", confidence_band: "HIGH", created_at: "2026-08-31T10:00:00Z", material_change_count: 1, exposure_types: ["MERCHANT_PAYMENTS"], stakes_types: ["RELIABILITY"], guidance_status: "READY", gaps_summary: "The final implementation date needs validation.", response_options: [{ option_code: "ESCALATE", title: "Start an applicability review", description: "Bring Product and Compliance together around the evidence.", tradeoffs: ["Uses specialist review capacity"] }], next_validation_steps: ["Confirm the authoritative implementation deadline."], evidence: [{ id: "40000000-0000-4000-8000-000000000001", title: "Authoritative circular", source_name: "CBN", confidence_band: "HIGH", source_url: "https://www.cbn.gov.ng/" }], actions: [], timeline: [{ event_type: "BRIEF_CREATED", created_at: "2026-08-31T10:00:00Z" }]
};

async function authenticatedApi(page: Page, permissionRole = "ADMIN", phase5Ui = true) {
  await page.route("**/api/v1/auth/refresh", (route) => route.fulfill({ json: { access_token: "test-token", expires_in: 900, user: { ...user, permission_role: permissionRole } } }));
  await page.route("**/api/v1/alerts", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/events", (route) => route.fulfill({ status: 202, json: { accepted: true } }));
  await page.route("**/api/v1/capabilities", (route) => route.fulfill({ json: { phase5_brief_lifecycle_enabled: phase5Ui, phase5_new_ui_enabled: phase5Ui } }));
}

async function pilotProductApi(page: Page) {
  await authenticatedApi(page);
  await page.route("**/api/v1/briefs", (route) => route.fulfill({ json: [brief] }));
  await page.route(`**/api/v1/briefs/${briefId}`, (route) => route.fulfill({ json: brief }));
  await page.route("**/api/v1/relevant-monitoring**", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/briefing/changes", (route) => route.fulfill({ json: { new_briefs: 1, updated_briefs: 0, new_evidence_items: 1, new_relevant_monitoring: 0 } }));
  await page.route("**/api/v1/company/briefs", (route) => route.fulfill({ json: { profile: { company_type: "Payments fintech", headquarters_country: "Nigeria", strategic_priorities: ["Transaction reliability"], operating_markets: ["Nigeria"] }, briefs: [brief] } }));
  await page.route("**/api/v1/watchlist", (route) => route.fulfill({ json: { company: [{ id: "80000000-0000-4000-8000-000000000001", name: "NIBSS", object_type: "DEPENDENCY", importance: "HIGH", recent_activity_count: 1, open_brief_count: 1 }], focus: [{ id: "90000000-0000-4000-8000-000000000001", label: "Merchant profitability", focus_type: "TOPIC", recent_activity_count: 2, open_brief_count: 1 }] } }));
  await page.route("**/api/v1/signals", (route) => route.fulfill({ json: [{ id: "a0000000-0000-4000-8000-000000000001", signal_id: "40000000-0000-4000-8000-000000000001", title: "Verified infrastructure update", global_implication: "Payment operators should review service dependencies.", primary_domain: "INFRASTRUCTURE", urgency_band: "MODERATE", confidence_band: "HIGH", source_name: "NIBSS" }] }));
  await page.route("**/api/v1/alerts", (route) => route.fulfill({ json: [{ id: "b0000000-0000-4000-8000-000000000001", brief_id: briefId, priority: "HIGH", subject: "Settlement implementation review", status: "DELIVERED", created_at: "2026-08-31T10:00:00Z", payload: { why_delivered: "Matches your settlement Focus Area." } }] }));
  await page.route("**/api/v1/digests", (route) => route.fulfill({ json: [{ id: "c0000000-0000-4000-8000-000000000001", period_start: "2026-08-24T00:00:00Z", period_end: "2026-08-31T00:00:00Z", status: "SENT", brief_ids: [briefId], content: { latest_brief: { what_changed: brief.what_changed, priority: "HIGH" } } }] }));
}

test("accepts a single-use pilot invitation", async ({ page }) => {
  const token = "a".repeat(64);
  await page.route("**/api/v1/auth/invitations/validate**", (route) => route.fulfill({ json: { valid: true, workspace_name: "Pilot Payments", email: "p***@example.com", expires_at: "2026-09-02T10:00:00Z" } }));
  let accepted = false;
  await page.route("**/api/v1/auth/invitations/accept", async (route) => { const body = route.request().postDataJSON(); accepted = body.token === token && body.display_name === "Ada Okafor"; await route.fulfill({ json: { access_token: "test-token", expires_in: 900, user } }); });
  await page.route("**/api/v1/compliance/**", (route) => route.fulfill({ json: [] }));
  await page.goto(`/invite/accept?token=${token}`);
  await expect(page.getByRole("heading", { name: "Join Pilot Payments" })).toBeVisible();
  await page.getByLabel("Your name").fill("Ada Okafor");
  await page.getByLabel("Create password").fill("correct horse battery staple");
  await page.getByRole("button", { name: "Accept invitation" }).click();
  await expect.poll(() => accepted).toBe(true);
  await expect(page).toHaveURL(/\/onboarding\/legal/);
});

test("renders the evidence-first briefing and responsive monitoring", async ({ page }) => {
  await authenticatedApi(page);
  await page.route("**/api/v1/briefs", (route) => route.fulfill({ json: [brief] }));
  await page.route("**/api/v1/relevant-monitoring**", (route) => route.fulfill({ json: [{ id: "50000000-0000-4000-8000-000000000001", headline: "NIBSS publishes a routine availability update.", relevance_reasons: ["Infrastructure"], primary_domain: "INFRASTRUCTURE", detected_at: "2026-08-31T11:00:00Z" }] }));
  await page.route("**/api/v1/briefing/changes", (route) => route.fulfill({ json: { new_briefs: 1, updated_briefs: 1, new_evidence_items: 2, new_relevant_monitoring: 1 } }));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/briefing");
  await expect(page.getByRole("heading", { name: /Good (morning|afternoon|evening), Ada/ })).toBeVisible();
  await expect(page.getByText("A new settlement rule changes the implementation timeline.").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Below the decision threshold" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("uses the legacy product experience while the new UI flag is off", async ({ page }) => {
  await authenticatedApi(page, "ADMIN", false);
  await page.route("**/api/v1/briefs", (route) => route.fulfill({ json: [brief] }));
  await page.goto("/briefing");
  await expect(page.getByRole("heading", { name: "Developments requiring attention" })).toBeVisible();
  await expect(page.getByText(brief.what_changed).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Below the decision threshold" })).not.toBeVisible();
});

test("opens a Decision Brief, evidence, Decision Paths, and records an action", async ({ page }) => {
  await authenticatedApi(page);
  await page.route(`**/api/v1/briefs/${briefId}`, (route) => route.fulfill({ json: brief }));
  let action = "";
  await page.route(`**/api/v1/briefs/${briefId}/actions`, async (route) => { action = route.request().postDataJSON().action_type; await route.fulfill({ status: 201, json: { id: "60000000-0000-4000-8000-000000000001", action_type: action } }); });
  await page.goto(`/briefs/${briefId}`);
  await expect(page.getByRole("heading", { name: "Decision Paths" })).toBeVisible();
  await page.getByRole("button", { name: /Evidence/ }).click();
  await expect(page.getByText("Authoritative circular")).toBeVisible();
  await page.getByRole("button", { name: "Acknowledge" }).click();
  await expect.poll(() => action).toBe("ACKNOWLEDGED");
});

test("keeps the operator console behind MFA-authenticated system admin identity", async ({ page }) => {
  await page.route("**/api/v1/auth/admin/mfa", (route) => route.fulfill({ json: { access_token: "admin-token", expires_in: 900, user: { ...user, permission_role: "SYSTEM_ADMIN" } } }));
  await page.route("**/api/v1/internal/admin/tenants", (route) => route.fulfill({ json: [{ id: user.workspace_id, name: "Pilot Payments", status: "TRIAL", pilot_status: "SETUP", pilot_owner: "Stem", pending_invites: 0 }] }));
  await page.goto("/internal/login");
  await page.getByLabel("Email").fill("operator@example.com");
  await page.getByLabel("Password").fill("operator-password");
  await page.getByLabel("Authenticator code").fill("123456");
  await page.getByRole("button", { name: "Continue securely" }).click();
  await expect(page).toHaveURL(/\/internal\/admin\/tenants/);
  await expect(page.getByRole("heading", { name: "Pilot tenants" })).toBeVisible();
});

test("logs in and loads an evidence-backed customer workspace", async ({ page }) => {
  let submitted = false;
  await page.route("**/api/v1/auth/login", async (route) => {
    submitted = route.request().postDataJSON().email === "pilot@example.com";
    await route.fulfill({ json: { access_token: "test-token", expires_in: 900, user } });
  });
  await authenticatedApi(page);
  await page.route("**/api/v1/briefs", (route) => route.fulfill({ json: [brief] }));
  await page.route("**/api/v1/relevant-monitoring**", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/briefing/changes", (route) => route.fulfill({ json: { new_briefs: 1, updated_briefs: 0, new_evidence_items: 1, new_relevant_monitoring: 0 } }));
  await page.goto("/login");
  await page.getByLabel("Email").fill("pilot@example.com");
  await page.getByLabel("Password").fill("a-valid-password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect.poll(() => submitted).toBe(true);
  await expect(page).toHaveURL(/\/briefing/);
  await expect(page.getByRole("heading", { name: /Good (morning|afternoon|evening), Ada/ })).toBeVisible();
});

test("starts activation from the MFA-protected tenant console", async ({ page }) => {
  await authenticatedApi(page, "SYSTEM_ADMIN");
  const detail = {
    tenant: { id: user.workspace_id, name: "Pilot Payments", status: "TRIAL", pilot_status: "SETUP", pilot_owner: "Stem", internal_notes: "" },
    checklist: { company_context_complete: true, entities_reviewed: true, activation_complete: false, invite_accepted: false, first_value_ready: false },
    company_objects: [], users: [], invitations: [], activations: [], briefs: []
  };
  await page.route(`**/api/v1/internal/admin/tenants/${user.workspace_id}`, (route) => route.fulfill({ json: detail }));
  await page.route(`**/api/v1/internal/admin/tenants/${user.workspace_id}/metrics`, (route) => route.fulfill({ json: { time_to_first_value_seconds: null, brief_open_rate: 0, action_rate: 0, active_days: 0, event_counts: {} } }));
  let activated = false;
  await page.route(`**/api/v1/internal/admin/tenants/${user.workspace_id}/activation`, async (route) => { activated = route.request().method() === "POST"; await route.fulfill({ status: 202, json: { id: "70000000-0000-4000-8000-000000000001", status: "PENDING" } }); });
  await page.goto(`/internal/admin/tenants/${user.workspace_id}`);
  await page.getByRole("tab", { name: "Activation" }).click();
  await page.getByRole("button", { name: "Start activation" }).click();
  await expect.poll(() => activated).toBe(true);
});

test("denies a direct cross-tenant Decision Brief route without leaking data", async ({ page }) => {
  await authenticatedApi(page);
  await page.route(`**/api/v1/briefs/${briefId}`, (route) => route.fulfill({ status: 404, json: { detail: { code: "NOT_FOUND", message: "Decision Brief not found." } } }));
  await page.goto(`/briefs/${briefId}`);
  await expect(page.getByRole("heading", { name: "This view could not refresh." })).toBeVisible();
  await expect(page.getByText(brief.what_changed)).not.toBeVisible();
});

for (const width of [1440, 1024, 768, 390]) {
  test(`renders every pilot product surface at ${width}px without overflow`, async ({ page }, testInfo) => {
    await pilotProductApi(page);
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const routes = ["/briefing", `/briefs/${briefId}`, "/company", "/watchlist", "/intelligence", "/alerts", "/digests"];
    for (const route of routes) {
      await page.goto(route);
      await expect(page.locator("h1").first()).toBeVisible({ timeout: 15_000 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    }
    await testInfo.attach(`pilot-surfaces-${width}`, { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
  });
}
