import { expect, Page, test } from "@playwright/test";

test.setTimeout(120_000);
const eventually = expect.configure({timeout: 30_000});

async function auth(page: Page) {
  await page.route("**/api/v1/auth/refresh", route => route.fulfill({json: {access_token: "test-only", expires_in: 900, user: {id: "user", workspace_id: "tenant", permission_role: "ADMIN", display_name: "Reviewer", workspace_name: "Test governance"}}}));
  await page.route("**/api/v1/alerts", route => route.fulfill({json: []}));
}

test("evidence reviewer displays missing criteria and saves a reviewer override", async ({page}) => {
  await auth(page);
  await page.route("**/api/v1/artifacts**", route => route.fulfill({json: {items: [], total: 0}}));
  await page.route("**/api/v1/policies", route => route.fulfill({json: {items: [], health: {assessed_obligations: 1, policy_evidence_score: 0}}}));
  await page.route("**/api/v1/gap-audits/signals", route => route.fulfill({json: {items: [{id: "signal-1", title: "Record retention circular"}]}}));
  let audit = {id: "audit-1", run_id: "run-1", revision: 1, status: "gap_deficient", automated_status: "gap_deficient", compliance_score: 0, clause_reference: "1.1", requirement_title: "Retain customer records", source_excerpt: "Retain customer records for five years.", source_url: "https://cbn.gov.ng/", evidence_matches: [{criterion: "Retain records for five years", verdict: "missing", reasoning: "No policy found", evidence: []}], reviewer_override: null as null | {reason: string}};
  await page.route(/\/api\/v1\/gap-audits\?signal_id=/, route => route.fulfill({json: {run: {id: "run-1", processing_status: "completed"}, items: [audit]}}));
  await page.route("**/api/v1/gap-audits/audit-1/history", route => route.fulfill({json: {items: []}}));
  await page.route("**/api/v1/gap-audits/audit-1/override", async route => {
    const body = route.request().postDataJSON();
    expect(body.expected_revision).toBe(1); expect(body.status).toBe("adequately_met");
    audit = {...audit, revision: 2, status: body.status, reviewer_override: {reason: body.reason}};
    await route.fulfill({json: audit});
  });
  await page.goto("/artifacts?type=gap_matrix");
  await eventually(page.getByText("No verified policy evidence for this criterion.")).toBeVisible();
  await eventually(page.getByText(/500,000/)).toHaveCount(0);
  await page.getByLabel("Justification or sign-off note").fill("Reviewed approved supporting evidence.");
  await page.getByRole("combobox", {name: "Override status", exact: true}).selectOption("adequately_met");
  await page.getByRole("button", {name: "Override status", exact: true}).click();
  await eventually(page.getByText(/Reviewer override: Reviewed approved/)).toBeVisible();
});

test("policy vault uploads multipart files using the authenticated client", async ({page}) => {
  await auth(page);
  await page.route("**/api/v1/policies", route => route.fulfill({json: {items: [], health: {assessed_obligations: 0, policy_evidence_score: null}}}));
  let uploaded = false;
  await page.route("**/api/v1/policies/upload", async route => {
    expect(route.request().headers()["content-type"]).toContain("multipart/form-data; boundary=");
    expect(route.request().headers().authorization).toBe("Bearer test-only");
    uploaded = true;
    await route.fulfill({status: 202, json: {id: "policy-1", processing_status: "queued"}});
  });
  await page.goto("/settings/policies");
  await eventually(page.getByText("Not assessed", {exact: true})).toBeVisible();
  await page.getByLabel("Document title").fill("AML controls");
  await page.getByLabel("Policy document").setInputFiles({name: "policy.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.7 test fixture")});
  await page.getByRole("button", {name: "Upload and index"}).click();
  await eventually(page.getByRole("status")).toContainText("Upload received");
  expect(uploaded).toBe(true);
});

test("campaign checker highlights claims and keeps alternative wording subject to review", async ({page}) => {
  await auth(page);
  await page.route("**/api/v1/workspace/marketing/check", route => route.fulfill({json: {id: "check-1", status: "review_required", rules_version: "test", scope: "Selected advertising rules only.", approved: false, findings: [{rule_id: "investment_promises", severity: "high", start: 0, end: 27, excerpt: "Earn guaranteed 25% returns.", reason: "Substantiate this investment promise.", source_url: "https://sec.gov.ng/", reference: "SEC source", suggested_alternative: "Investment outcomes vary; review the risks."}]}}));
  await page.goto("/workspace/marketing");
  await page.getByLabel("Campaign copy").fill("Earn guaranteed 25% returns.");
  await page.getByRole("button", {name: "Check campaign"}).click();
  await eventually(page.locator("mark")).toContainText("guaranteed 25%");
  await eventually(page.getByText("Suggested wording — human review required")).toBeVisible();
  await page.getByLabel("Campaign copy").fill("Revised campaign copy for review.");
  await eventually(page.getByText(/Copy has changed/)).toBeVisible();
});
