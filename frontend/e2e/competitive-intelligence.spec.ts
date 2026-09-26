import { expect, Page, test } from "@playwright/test";

const eventually = expect.configure({timeout: 30_000});
const source = {id: "web:0", kind: "public_web", title: "AcmePay pricing", url: "https://acmepay.example/pricing", text: "Transfers cost NGN 20."};
const claim = {value: "NGN 20 per transfer", citations: [{source_id: "web:0", excerpt: "Transfers cost NGN 20."}]};
const dossier = {id: "dossier-1", competitor_name: "AcmePay", canonical_domain: "acmepay.example", processing_status: "ready", error_code: null, last_refreshed_at: "2026-09-25T12:00:00Z", known_licenses: [], primary_settlement_rails: [], core_target_segments: [], fee_model_summary: "NGN 20 per transfer", strengths_vs_us: [], weaknesses_vs_us: [], profile: {fee_model: claim, unknowns: ["Sponsor bank not established."]}, evidence: [source], provenance: {live_search_available: true}, battlecards: [{id: "artifact-1", title: "AcmePay changes its pricing", urgency: "high"}]};
const deal = {id: "deal-1", competitor_id: "dossier-1", competitor_name_raw: "AcmePay", deal_outcome: "won", merchant_segment: "Retail checkout", deal_size_arr_or_gmv: "NGN 40M monthly GMV", occurred_on: "2026-09-24", processing_status: "ready", error_code: null, extracted_decision_drivers: ["Same-day settlement"], objections_encountered: ["Setup fee"], winning_talk_track: "We demonstrated webhook retries.", talk_track_kind: "observed", raw_sales_notes: "Merchant chose same-day settlement. We demonstrated webhook retries.", extraction: {decision_drivers: [{point: "Same-day settlement", theme: "settlement", excerpt: "Merchant chose same-day settlement."}]}};
const insights = {metrics: {reported: 2, analyzed: 2, won: 1, lost: 1, churned: 0, pending: 0, failed: 0, win_rate: 50, win_rate_denominator: 2}, themes: [{theme: "settlement", deal_outcome: "won", count: 1}], recent_signals: [deal], objections: [{objection: "Setup fee", count: 1, source_ids: ["deal-1"]}], filters: {competitor_name: "AcmePay", start_date: "2026-07-01", end_date: "2026-09-30"}, metric_definition: "Won / (won + lost) among analyzed field reports. Churn is counted separately."};

async function auth(page: Page) {
  await page.route("**/api/v1/auth/refresh", route => route.fulfill({json: {access_token: "test-only", expires_in: 900, user: {id: "user", workspace_id: "tenant", permission_role: "ADMIN", display_name: "Reviewer", workspace_name: "Test sales"}}}));
  await page.route("**/api/v1/alerts", route => route.fulfill({json: []}));
  await page.route("**/api/v1/competitors/dossiers", route => route.fulfill({json: {items: [dossier]}}));
  await page.route("**/api/v1/competitors/dossiers/dossier-1", route => route.fulfill({json: dossier}));
  await page.route("**/api/v1/competitors/win-loss-insights?**", route => route.fulfill({json: insights}));
  await page.route("**/api/v1/competitors/deal-signals/deal-1", route => route.fulfill({json: deal}));
}

test("dossiers expose source evidence, unknowns, linked battlecards and field insights", async ({page}) => {
  await auth(page);
  await page.route("**/api/v1/artifacts**", route => route.fulfill({json: {items: [], total: 0}}));
  let requested = false;
  await page.route("**/api/v1/competitors/dossiers/generate", async route => { expect(route.request().postDataJSON().competitor_name).toBe("AcmePay"); requested = true; await route.fulfill({status: 202, json: dossier}); });
  await page.goto("/artifacts?type=battlecard");
  await eventually(page.getByRole("heading", {name: "Competitor dossiers"})).toBeVisible();
  await page.getByLabel("Competitor to research").fill("AcmePay");
  await page.getByRole("button", {name: "Generate dossier"}).click();
  await eventually(page.getByText("NGN 20 per transfer", {exact: true})).toBeVisible();
  await page.getByText("Supporting evidence (1)").click();
  await eventually(page.getByRole("link", {name: "AcmePay pricing"})).toHaveAttribute("href", source.url!);
  await eventually(page.getByText("Sponsor bank not established.")).toBeVisible();
  await eventually(page.getByRole("link", {name: "AcmePay changes its pricing"})).toBeVisible();
  await eventually(page.getByText("50%", {exact: true})).toBeVisible();
  await page.getByRole("button", {name: "Inspect field evidence"}).click();
  await eventually(page.getByLabel("Field report evidence")).toContainText(deal.raw_sales_notes);
  expect(requested).toBe(true);
});

test("global quick intake persists a field report then shows extracted drivers", async ({page}) => {
  await auth(page);
  await page.route("**/api/v1/artifacts**", route => route.fulfill({json: {items: [], total: 0}}));
  let saved = false;
  await page.route("**/api/v1/competitors/deal-signals", async route => {
    const body = route.request().postDataJSON();
    expect(body.deal_outcome).toBe("won"); expect(body.raw_sales_notes).toContain("same-day"); expect(body.idempotency_key).toBeTruthy();
    saved = true;
    await route.fulfill({status: 202, json: {...deal, processing_status: "queued"}});
  });
  await page.goto("/artifacts?type=battlecard");
  await page.getByRole("button", {name: "Log deal signal"}).click();
  const dialog = page.getByRole("dialog", {name: "Log deal signal"});
  await dialog.getByLabel("Competitor", {exact: true}).fill("AcmePay");
  await dialog.getByLabel("Merchant segment").fill("Retail checkout");
  await dialog.getByLabel("Sales notes").fill(deal.raw_sales_notes);
  await dialog.getByRole("button", {name: "Save and extract insights"}).click();
  await eventually(dialog.getByRole("status")).toContainText("Field report saved");
  await eventually(dialog.getByRole("heading", {name: "Decision drivers"})).toBeVisible();
  await eventually(dialog.getByText("Same-day settlement", {exact: true})).toBeVisible();
  expect(saved).toBe(true);
});

test("deep competitive workspace mode renders scoped metrics and citations", async ({page}) => {
  await auth(page);
  const session = {id: "session-1", organization_id: "tenant", title: "Competitive research", created_at: "2026-09-25T12:00:00Z", updated_at: "2026-09-25T12:00:00Z"};
  await page.route("**/api/v1/workspace/sessions?**", route => route.fulfill({json: {sessions: [session], total_count: 1}}));
  await page.route("**/api/v1/workspace/sessions/session-1/messages", async route => {
    if (route.request().method() === "GET") { await route.fulfill({json: {session, messages: []}}); return; }
    expect(route.request().postDataJSON().mode).toBe("competitive");
    const synthesis = {operational_exposure: "One win and one loss were reported in this scope.", context_and_precedents: "Settlement was a reported decision factor.", role_action_items: [], cited_artifact_ids: [], web_sources: []};
    await route.fulfill({json: {session_id: session.id, synthesis, competitive_research: {...insights, status: "ready", scope_notes: ["Quarter interpreted in 2026."], sources: [source], playbook: {findings: [claim], recommended_actions: [], limitations: []}}, assistant_message: {id: "message-1", session_id: session.id, organization_id: "tenant", role: "assistant", content: JSON.stringify(synthesis), created_at: session.created_at}}});
  });
  await page.goto("/workspace?mode=competitive");
  await eventually(page.getByLabel("Deep competitive research")).toBeChecked();
  await page.getByPlaceholder(/Ask Cogent/).fill("What is our win rate against AcmePay in Q3?");
  await page.getByRole("button", {name: "Send query"}).click();
  const result = page.getByLabel("Competitive research results");
  await eventually(result).toContainText("50%");
  await eventually(result).toContainText("2026-07-01 to 2026-09-30");
  await result.getByText("Supporting evidence (1)").click();
  await eventually(result.getByRole("link", {name: "AcmePay pricing"})).toBeVisible();
});
