"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useCallback, useEffect, useState } from "react";

import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

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
                {tab === "Team" && <ResourcePanel resource={state.data.team} retry={load}>{(team) => <SettingsPanel title="Team" description="Workspace membership is isolated to your company.">{team === null ? <div className="settings-empty"><p>Team membership is available to workspace administrators.</p></div> : <div className="team-list">{team.map((member) => <article key={member.id}><div><strong>{member.display_name || member.email}</strong><span>{member.email}</span></div><i>{permissionLabel(member.permission_role)}</i><span>{member.status}</span></article>)}</div>}<div className="access-summary"><small>Team invitations are managed by Stem during your guided pilot.</small></div></SettingsPanel>}</ResourcePanel>}
                {tab === "Billing" && <SettingsPanel title="Billing" description="Review your trial, plan, and secure Paystack checkout."><div className="billing-summary"><p className="eyebrow">Current plan</p><h3>{state.data.me.plan_code}</h3><span>{state.data.me.billing_status.replaceAll("_", " ")}</span><Link className="primary-button" href="/settings/billing">View plans & billing</Link></div></SettingsPanel>}
                {tab === "API / Integrations" && <ResourcePanel resource={state.data.integrations} retry={load}>{(integrations) => <SettingsPanel title="API / Integrations" description="Connections available for your current plan."><div className="integration-list"><article><strong>Stem Cogent API</strong><span>{integrations.api_enabled ? `${integrations.api_keys.length} active API key${integrations.api_keys.length === 1 ? "" : "s"}` : `Not included in ${integrations.plan_code}`}</span><i>{integrations.api_enabled ? "Enabled" : "Plan gated"}</i></article><article><strong>Private company data</strong><span>{integrations.private_uploads ? "Private data connections are managed with Stem during your guided pilot." : `Not included in ${integrations.plan_code}`}</span><i>{integrations.private_uploads ? "Available" : "Plan gated"}</i></article></div></SettingsPanel>}</ResourcePanel>}
              </>
            )}
          </div>
        </div>
      </section>
    </WorkspaceShell>
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
