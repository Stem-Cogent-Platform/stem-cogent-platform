"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useCallback, useEffect, useState } from "react";

import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest, createCheckout, getOnboardingStatus, inviteTeamMember } from "@/lib/api";
import { LoadState, OnboardingStatus } from "@/lib/types";

type Me = { display_name: string; email: string; workspace_name: string; permission_role: string; plan_code: string; billing_status: string };
type Lens = null | { role_code: string; responsibility_tags: string[]; priority_domains: string[]; delivery_preference: string };
type Focus = { id: string; label: string; focus_type: string; weight: number }[];
type Company = { profile: null | { profile_completeness: number; operating_markets: string[]; strategic_priorities: string[] }; objects: { id: string; name: string; object_type: string }[]; context_status: { complete: boolean; completeness: number; version: number } };
type Alerts = { domain_codes: string[]; urgency_bands: string[]; delivery_channels: string[]; digest_frequency: string; enabled: boolean };
type TeamMember = { id: string; email: string; display_name?: string; permission_role: string; status: string; mfa_enabled: boolean; last_login_at?: string };
type Integrations = { plan_code: string; api_enabled: boolean; private_uploads: boolean | number; api_keys: { id: string; name: string; key_prefix: string; status: string; last_used_at?: string }[] };
type Resource<T> = { data: T; error?: never } | { data?: never; error: string };
type SettingsData = { me: Me; lens: Resource<Lens>; focus: Resource<Focus>; company: Resource<Company>; alerts: Resource<Alerts>; team: Resource<TeamMember[] | null>; integrations: Resource<Integrations> };

const tabs = ["Profile", "Decision Lens", "Focus Areas", "Company Context", "Alerts & Digests", "Team", "Billing", "API / Integrations"] as const;
const alertDomains = [["REGULATORY_POLICY", "Regulatory"], ["COMPETITIVE_PRODUCT", "Competitive product"], ["INFRASTRUCTURE_RELIABILITY", "Infrastructure"], ["CUSTOMER_MARKET", "Customer & market"], ["FINANCIAL_ECONOMIC", "Financial & economic"], ["CAPITAL_PARTNERSHIP", "Capital & partnership"], ["MARKET_EXPANSION", "Market expansion"], ["FRAUD_RISK_TRUST", "Fraud, risk & trust"]] as const;

function permissionLabel(role: string) {
  return role === "ADMIN" ? "Workspace administrator" : role.replaceAll("_", " ");
}

async function resource<T>(request: Promise<T>): Promise<Resource<T>> {
  try {
    return { data: await request };
  } catch (error) {
    return { error: error instanceof Error ? error.message : "This settings section could not be loaded." };
  }
}

export default function SettingsPage() {
  const [tab, setTab] = useState<(typeof tabs)[number]>("Profile");
  const [state, setState] = useState<LoadState<SettingsData>>({ status: "loading" });
  const [message, setMessage] = useState("");
  const [savingAlerts, setSavingAlerts] = useState(false);

  const load = useCallback(async () => {
    try {
      setState({ status: "loading" });
      const me = await apiRequest<Me>("/api/v1/auth/me");
      const [lens, focus, company, alerts, team, integrations] = await Promise.all([
        resource(apiRequest<Lens>("/api/v1/me/decision-lens")),
        resource(apiRequest<Focus>("/api/v1/me/focus-areas")),
        resource(apiRequest<Company>("/api/v1/context/company")),
        resource(apiRequest<Alerts>("/api/v1/alert-preferences")),
        me.permission_role === "ADMIN" ? resource(apiRequest<TeamMember[]>("/api/v1/team")) : Promise.resolve<Resource<null>>({ data: null }),
        resource(apiRequest<Integrations>("/api/v1/integrations"))
      ]);
      setState({ status: "ready", data: { me, lens, focus, company, alerts, team, integrations } });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Settings could not be loaded." });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function saveAlerts(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setMessage("");
    setSavingAlerts(true);
    try {
      await apiRequest("/api/v1/alert-preferences", { method: "PUT", body: JSON.stringify({
        domain_codes: form.getAll("domain"), urgency_bands: form.getAll("urgency"),
        delivery_channels: form.getAll("channel"), minimum_relevance_band: null,
        digest_frequency: form.get("digest"), enabled: true
      }) });
      setMessage("Alert and digest preferences saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Preferences could not be saved.");
    } finally {
      setSavingAlerts(false);
    }
  }

  return (
    <WorkspaceShell>
      <section className="settings-page">
        <div className="page-heading"><div><p className="eyebrow">Workspace controls</p><h1>Settings</h1><p>Manage your relevance profile, delivery preferences, team, and plan.</p></div></div>
        <Link href="/settings/policies" className="text-sm font-semibold text-blue-700 underline">Policy governance vault</Link>
        <div className="settings-layout">
          <nav aria-label="Settings sections" className="settings-tabs">{tabs.map((item) => <button aria-current={tab === item ? "page" : undefined} className={tab === item ? "active" : ""} key={item} onClick={() => setTab(item)} type="button">{item}</button>)}</nav>
          <div className="settings-content">
            {state.status === "loading" && <ModuleLoading label="Loading settings" />}
            {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
            {state.status === "ready" && (
              <>
                {tab === "Profile" && <SettingsPanel title="Profile" description="Your identity and active company workspace."><dl className="settings-definition"><div><dt>Name</dt><dd>{state.data.me.display_name}</dd></div><div><dt>Work email</dt><dd>{state.data.me.email}</dd></div><div><dt>Company</dt><dd>{state.data.me.workspace_name}</dd></div><div><dt>Workspace access</dt><dd>{permissionLabel(state.data.me.permission_role)}</dd></div></dl></SettingsPanel>}
                {tab === "Decision Lens" && <ResourcePanel resource={state.data.lens} retry={load}>{(lens) => <SettingsPanel title="Decision Lens" description="Controls how Decision Briefs are ranked and explained for your role.">{lens ? <dl className="settings-definition"><div><dt>Role</dt><dd>{lens.role_code.replaceAll("_", " ")}</dd></div><div><dt>Priorities</dt><dd>{lens.priority_domains.join(", ") || "Not configured"}</dd></div><div><dt>Responsibilities</dt><dd>{lens.responsibility_tags.join(", ") || "Not configured"}</dd></div><div><dt>Delivery</dt><dd>{lens.delivery_preference.replaceAll("_", " ")}</dd></div></dl> : <EmptySettings text="Your Decision Lens is not configured." action="Configure now" href="/onboarding" />}</SettingsPanel>}</ResourcePanel>}
                {tab === "Focus Areas" && <ResourcePanel resource={state.data.focus} retry={load}>{(focus) => <SettingsPanel title="Focus Areas" description="Temporary or persistent subjects that deserve extra attention.">{focus.length ? <div className="settings-tag-list">{focus.map((item) => <span key={item.id}>{item.label}<small>{item.focus_type.replaceAll("_", " ")}</small></span>)}</div> : <EmptySettings text="No personal Focus Areas are active." action="Add focus areas" href="/onboarding" />}</SettingsPanel>}</ResourcePanel>}
                {tab === "Company Context" && <ResourcePanel resource={state.data.company} retry={load}>{(company) => <SettingsPanel title="Company Context" description={`Shared business context used to establish company-specific relevance · version ${company.context_status.version}.`}><div className="context-completeness"><span><i style={{ width: `${Math.round(company.context_status.completeness * 100)}%` }} /></span><strong>{Math.round(company.context_status.completeness * 100)}% complete</strong></div><div className="settings-tag-list">{company.objects.map((item) => <span key={item.id}>{item.name}<small>{item.object_type.replaceAll("_", " ")}</small></span>)}</div>{!company.context_status.complete && <EmptySettings text="Complete the required Company Context fields to improve relevance." action="Complete context" href="/onboarding" />}</SettingsPanel>}</ResourcePanel>}
                {tab === "Alerts & Digests" && <ResourcePanel resource={state.data.alerts} retry={load}>{(alerts) => <SettingsPanel title="Alerts & Digests" description="Choose what interrupts you and how summaries are delivered."><form className="preferences-form" onSubmit={saveAlerts}><fieldset><legend>Domains</legend>{alertDomains.map(([value, label]) => <label key={value}><input defaultChecked={alerts.domain_codes.includes(value)} name="domain" type="checkbox" value={value} /><span>{label}</span></label>)}</fieldset><fieldset><legend>Urgency</legend>{["CRITICAL", "HIGH", "MEDIUM"].map((item) => <label key={item}><input defaultChecked={alerts.urgency_bands.includes(item)} name="urgency" type="checkbox" value={item} /><span>{item}</span></label>)}</fieldset><fieldset><legend>Channels</legend>{[["IN_APP", "In app"], ["EMAIL", "Email"]].map(([value, label]) => <label key={value}><input defaultChecked={alerts.delivery_channels.includes(value)} name="channel" type="checkbox" value={value} /><span>{label}</span></label>)}</fieldset><label className="select-field"><span>Digest frequency</span><select defaultValue={alerts.digest_frequency} name="digest"><option value="DAILY">Daily</option><option value="WEEKLY">Weekly</option><option value="NONE">None</option></select></label><button className="primary-button" disabled={savingAlerts} type="submit">{savingAlerts ? "Saving…" : "Save preferences"}</button>{message && <p aria-live="polite" className="form-message">{message}</p>}</form></SettingsPanel>}</ResourcePanel>}
                {tab === "Team" && (
                  <ResourcePanel resource={state.data.team} retry={load}>
                    {(team) => (
                      <TeamSettingsPanel team={team} onInviteSuccess={load} />
                    )}
                  </ResourcePanel>
                )}
                {tab === "Billing" && (
                  <BillingSettingsPanel me={state.data.me} />
                )}
                {tab === "API / Integrations" && <ResourcePanel resource={state.data.integrations} retry={load}>{(integrations) => <SettingsPanel title="API / Integrations" description="Connections available for your current plan."><div className="integration-list"><article><strong>Stem Cogent API</strong><span>{integrations.api_enabled ? `${integrations.api_keys.length} active API key${integrations.api_keys.length === 1 ? "" : "s"}` : `Not included in ${integrations.plan_code}`}</span><i>{integrations.api_enabled ? "Enabled" : "Plan gated"}</i></article><article><strong>Private company data</strong><span>{integrations.private_uploads ? "Private data connections are managed with Stem during your guided pilot." : `Not included in ${integrations.plan_code}`}</span><i>{integrations.private_uploads ? "Available" : "Plan gated"}</i></article></div></SettingsPanel>}</ResourcePanel>}
              </>
            )}
          </div>
        </div>
      </section>
    </WorkspaceShell>
  );
}

function TeamSettingsPanel({
  team,
  onInviteSuccess,
}: {
  team: TeamMember[] | null;
  onInviteSuccess: () => Promise<void>;
}) {
  const [inviteEmail, setInviteEmail] = useState("");
  const [assignedLens, setAssignedLens] = useState<"executive_strategy" | "compliance_legal" | "product_engineering" | "treasury_reconciliation">("executive_strategy");
  const [isInviting, setIsInviting] = useState(false);
  const [inviteResult, setInviteResult] = useState<{
    email: string;
    token: string;
    otp_code: string;
    expires_at: string;
  } | null>(null);
  const [inviteError, setInviteError] = useState<string | null>(null);

  async function handleCreateInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setIsInviting(true);
    setInviteError(null);
    setInviteResult(null);

    try {
      const res = await apiRequest<{
        success: boolean;
        email: string;
        token: string;
        otp_code: string;
        expires_at: string;
      }>("/api/v1/onboarding/invite", {
        method: "POST",
        body: JSON.stringify({
          email: inviteEmail.trim(),
          assigned_lens: assignedLens,
        }),
      });
      setInviteResult(res);
      setInviteEmail("");
      void onInviteSuccess();
    } catch (err) {
      setInviteError(err instanceof Error ? err.message : "Failed to generate teammate invitation.");
    } finally {
      setIsInviting(false);
    }
  }

  return (
    <SettingsPanel
      title="Team & Visual Seat Manager"
      description="Manage workspace seats, generate secure OTP invitation tokens, and assign role lenses."
    >
      {/* Invite Generator Form */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-5 space-y-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
              One-Click Teammate Invite Generation
            </h3>
            <p className="text-[11px] text-slate-500">
              Generates a cryptographically signed invitation token bound to your tenant organization.
            </p>
          </div>
          <span className="text-[11px] font-mono text-blue-600 font-bold bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
            POST /api/v1/organizations/invitations
          </span>
        </div>

        <form onSubmit={handleCreateInvite} className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <input
            type="email"
            required
            placeholder="colleague@fintech.com"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-300 bg-white text-xs text-slate-900 focus:outline-none focus:border-blue-600 sm:col-span-1 shadow-2xs font-medium"
          />

          <select
            value={assignedLens}
            onChange={(e) => setAssignedLens(e.target.value as typeof assignedLens)}
            className="h-10 px-3 rounded-lg border border-slate-300 bg-white text-xs text-slate-900 focus:outline-none focus:border-blue-600 sm:col-span-1 shadow-2xs font-medium"
          >
            <option value="executive_strategy">Executive Strategy (CEO)</option>
            <option value="compliance_legal">Compliance & Legal</option>
            <option value="product_engineering">Product & Engineering</option>
            <option value="treasury_reconciliation">Treasury & Settlement</option>
          </select>

          <button
            type="submit"
            disabled={isInviting}
            className="h-10 px-4 rounded-lg bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 active:scale-95 transition shadow-2xs flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            {isInviting ? "Generating..." : "Generate Invite Token →"}
          </button>
        </form>

        {inviteError && (
          <div className="rounded-lg bg-red-50 p-2.5 text-xs text-red-700 border border-red-200">
            {inviteError}
          </div>
        )}

        {inviteResult && (
          <div className="rounded-xl border border-emerald-300 bg-emerald-50/70 p-4 space-y-2 text-xs">
            <div className="flex items-center justify-between text-emerald-900 font-bold">
              <span>✓ Invitation Generated for {inviteResult.email}</span>
              <span className="font-mono text-[11px]">Valid for 7 days</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="p-2.5 rounded-lg bg-white border border-emerald-200">
                <span className="text-[10px] text-slate-500 block uppercase">6-Digit Verification OTP</span>
                <span className="text-base font-mono font-bold text-slate-900 tracking-wider">
                  {inviteResult.otp_code}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-white border border-emerald-200 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-500 block uppercase">Token Link</span>
                  <span className="text-[11px] font-mono text-blue-700 truncate max-w-[200px] block">
                    /invite/accept?token={inviteResult.token.slice(0, 14)}...
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const fullUrl = `${window.location.origin}/invite/accept?token=${inviteResult.token}`;
                    void navigator.clipboard.writeText(fullUrl);
                    alert("Copied full invitation link to clipboard!");
                  }}
                  className="px-2 py-1 rounded bg-slate-100 text-[11px] font-bold text-slate-700 hover:bg-slate-200"
                >
                  Copy Link
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Active Team Seat List */}
      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
        Active Workspace Members
      </h4>
      {team === null || team.length === 0 ? (
        <div className="settings-empty">
          <p>No other teammates invited yet. Use the invite generator above to add members.</p>
        </div>
      ) : (
        <div className="team-list">
          {team.map((member) => (
            <article key={member.id} className="flex items-center justify-between p-3 rounded-xl border border-slate-200 bg-white">
              <div>
                <strong>{member.display_name || member.email}</strong>
                <span className="block text-xs text-slate-500">{member.email}</span>
              </div>
              <div className="flex items-center gap-2">
                <i className="not-italic text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                  {permissionLabel(member.permission_role)}
                </i>
                <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                  {member.status}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}
    </SettingsPanel>
  );
}

function BillingSettingsPanel({ me }: { me: Me }) {
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null);
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);

  useEffect(() => {
    void getOnboardingStatus().then((res) => setOnboardingStatus(res)).catch(() => {});
  }, []);

  const pilotDaysRemaining = onboardingStatus?.pilot_days_remaining ?? 12;
  const totalTrialDays = 14;
  const elapsedDays = Math.max(0, totalTrialDays - pilotDaysRemaining);
  const percentRemaining = Math.round((pilotDaysRemaining / totalTrialDays) * 100);

  async function handleTriggerUpgrade(planCode: string) {
    setIsCheckingOut(true);
    setCheckoutError(null);
    try {
      const res = await createCheckout(planCode);
      if (res.authorization_url) {
        window.location.assign(res.authorization_url);
      }
    } catch (err) {
      setCheckoutError(err instanceof Error ? err.message : "Failed to initialize Paystack checkout.");
      setIsCheckingOut(false);
    }
  }

  return (
    <SettingsPanel
      title="Subscription & Billing Controls"
      description="14-day trial countdown status, query quotas, and official Paystack upgrade gateway."
    >
      {/* 14-Day Trial Countdown Progress Bar */}
      <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-6 space-y-4 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-blue-600 animate-pulse" />
              <span className="text-xs font-bold uppercase tracking-wider text-blue-900">
                14-Day Enterprise Trial Status
              </span>
            </div>
            <p className="mt-1 text-sm font-semibold text-slate-800">
              {pilotDaysRemaining} days remaining in your guided intelligence trial
            </p>
          </div>
          <div className="text-left sm:text-right font-mono">
            <span className="text-xl font-black text-blue-950">{pilotDaysRemaining} / 14</span>
            <span className="text-xs text-blue-700 block">Days Left</span>
          </div>
        </div>

        {/* Visual Countdown Progress Bar */}
        <div className="space-y-1">
          <div className="w-full h-3 rounded-full bg-blue-200/80 overflow-hidden border border-blue-300">
            <div
              className="h-full bg-blue-600 transition-all duration-500 rounded-full"
              style={{ width: `${percentRemaining}%` }}
            />
          </div>
          <div className="flex justify-between text-[11px] text-blue-800 font-mono">
            <span>Day {elapsedDays} elapsed</span>
            <span>{percentRemaining}% time remaining</span>
          </div>
        </div>
      </div>

      {checkoutError && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-xs text-red-700 border border-red-200">
          {checkoutError}
        </div>
      )}

      {/* Plan Details & Paystack Upgrade */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3 shadow-2xs">
          <span className="text-xs font-bold uppercase text-slate-400">Current Entitlement</span>
          <div className="text-lg font-black text-slate-900">{me.plan_code}</div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Status: <strong className="text-emerald-700 uppercase">{me.billing_status.replaceAll("_", " ")}</strong>
          </p>
          <div className="pt-2 border-t border-slate-100 text-xs text-slate-500 font-mono">
            Monthly Queries: {onboardingStatus?.queries_used_this_period || 0} / {onboardingStatus?.monthly_workspace_query_limit || 500}
          </div>
        </div>

        <div className="rounded-xl border border-slate-900 bg-slate-900 p-5 space-y-3 text-white shadow-md flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase text-blue-400">Upgrade Plan</span>
              <span className="text-[11px] font-mono text-emerald-400">Paystack Protected</span>
            </div>
            <div className="mt-1 text-lg font-black">Operator Growth Tier</div>
            <p className="text-xs text-slate-300 mt-1 leading-relaxed">
              Lock in full enterprise CBN gazette horizon monitoring, unlimited Copilot war room turns, and webhook uptime alerts.
            </p>
          </div>

          <button
            type="button"
            onClick={() => void handleTriggerUpgrade("operator_growth")}
            disabled={isCheckingOut}
            className="w-full h-10 rounded-lg bg-blue-600 text-white font-bold text-xs hover:bg-blue-500 active:scale-95 transition flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
          >
            {isCheckingOut ? "Connecting to Paystack..." : "Upgrade to Growth Tier via Paystack →"}
          </button>
        </div>
      </div>
    </SettingsPanel>
  );
}

function ResourcePanel<T>({ resource: value, retry, children }: { resource: Resource<T>; retry: () => Promise<void>; children: (data: T) => ReactNode }) {
  if ("error" in value) return <ModuleFailure message={value.error} retry={() => void retry()} />;
  return <>{children(value.data)}</>;
}

function SettingsPanel({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <section className="settings-panel"><header><h2>{title}</h2><p>{description}</p></header>{children}</section>;
}

function EmptySettings({ text, action, href }: { text: string; action: string; href: string }) {
  return <div className="settings-empty"><p>{text}</p><Link href={href}>{action} →</Link></div>;
}
