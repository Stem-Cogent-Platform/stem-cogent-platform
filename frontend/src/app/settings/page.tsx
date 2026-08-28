"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type SettingsData = {
  me: { display_name: string; email: string; workspace_name: string; permission_role: string; plan_code: string; billing_status: string };
  lens: null | { role_code: string; responsibility_tags: string[]; priority_domains: string[]; delivery_preference: string };
  focus: { id: string; label: string; focus_type: string; weight: number }[];
  company: { profile: null | { profile_completeness: number; operating_markets: string[]; strategic_priorities: string[] }; objects: { id: string; name: string; object_type: string }[] };
  alerts: { domain_codes: string[]; urgency_bands: string[]; delivery_channels: string[]; digest_frequency: string; enabled: boolean };
};

const tabs = ["Profile", "Decision Lens", "Focus Areas", "Company Context", "Alerts & Digests", "Team", "Billing", "API / Integrations"] as const;
const alertDomains = [["REGULATORY_POLICY", "Regulatory"], ["COMPETITIVE_PRODUCT", "Competitive product"], ["INFRASTRUCTURE_RELIABILITY", "Infrastructure"], ["CUSTOMER_MARKET", "Customer & market"], ["FINANCIAL_ECONOMIC", "Financial & economic"], ["CAPITAL_PARTNERSHIP", "Capital & partnership"], ["MARKET_EXPANSION", "Market expansion"], ["FRAUD_RISK_TRUST", "Fraud, risk & trust"]] as const;

export default function SettingsPage() {
  const [tab, setTab] = useState<(typeof tabs)[number]>("Profile");
  const [state, setState] = useState<LoadState<SettingsData>>({ status: "loading" });
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    try {
      const [me, lens, focus, company, alerts] = await Promise.all([
        apiRequest<SettingsData["me"]>("/api/v1/auth/me"),
        apiRequest<SettingsData["lens"]>("/me/decision-lens"),
        apiRequest<SettingsData["focus"]>("/me/focus-areas"),
        apiRequest<SettingsData["company"]>("/context/company"),
        apiRequest<SettingsData["alerts"]>("/api/v1/alert-preferences")
      ]);
      setState({ status: "ready", data: { me, lens, focus, company, alerts } });
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
    try {
      await apiRequest("/api/v1/alert-preferences", { method: "PUT", body: JSON.stringify({
        domain_codes: form.getAll("domain"), urgency_bands: form.getAll("urgency"),
        delivery_channels: form.getAll("channel"), minimum_relevance_band: null,
        digest_frequency: form.get("digest"), enabled: true
      }) });
      setMessage("Alert and digest preferences saved.");
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Preferences could not be saved."); }
  }

  return <WorkspaceShell><section className="settings-page"><div className="page-heading"><div><p className="eyebrow">Workspace controls</p><h1>Settings</h1><p>Manage your relevance profile, delivery preferences, team, and plan.</p></div></div>
    <div className="settings-layout"><nav className="settings-tabs" aria-label="Settings sections">{tabs.map((item) => <button aria-current={tab === item ? "page" : undefined} className={tab === item ? "active" : ""} onClick={() => setTab(item)} type="button" key={item}>{item}</button>)}</nav><div className="settings-content">
      {state.status === "loading" && <ModuleLoading />}{state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
      {state.status === "ready" && <>
        {tab === "Profile" && <SettingsPanel title="Profile" description="Your identity and active company workspace."><dl className="settings-definition"><div><dt>Name</dt><dd>{state.data.me.display_name}</dd></div><div><dt>Work email</dt><dd>{state.data.me.email}</dd></div><div><dt>Company</dt><dd>{state.data.me.workspace_name}</dd></div><div><dt>Permission</dt><dd>{state.data.me.permission_role}</dd></div></dl></SettingsPanel>}
        {tab === "Decision Lens" && <SettingsPanel title="Decision Lens" description="Controls how Decision Briefs are ranked and explained for your role.">{state.data.lens ? <dl className="settings-definition"><div><dt>Role</dt><dd>{state.data.lens.role_code.replaceAll("_", " ")}</dd></div><div><dt>Priorities</dt><dd>{state.data.lens.priority_domains.join(", ") || "Not configured"}</dd></div><div><dt>Responsibilities</dt><dd>{state.data.lens.responsibility_tags.join(", ") || "Not configured"}</dd></div><div><dt>Delivery</dt><dd>{state.data.lens.delivery_preference.replaceAll("_", " ")}</dd></div></dl> : <EmptySettings text="Your Decision Lens is not configured." action="Configure now" href="/onboarding" />}</SettingsPanel>}
        {tab === "Focus Areas" && <SettingsPanel title="Focus Areas" description="Temporary or persistent subjects that deserve extra attention.">{state.data.focus.length ? <div className="settings-tag-list">{state.data.focus.map((item) => <span key={item.id}>{item.label}<small>{item.focus_type.replaceAll("_", " ")}</small></span>)}</div> : <EmptySettings text="No personal Focus Areas are active." action="Add focus areas" href="/onboarding" />}</SettingsPanel>}
        {tab === "Company Context" && <SettingsPanel title="Company Context" description="Shared business context used to establish company-specific relevance."><div className="context-completeness"><span><i style={{width:`${Math.round((state.data.company.profile?.profile_completeness ?? 0)*100)}%`}} /></span><strong>{Math.round((state.data.company.profile?.profile_completeness ?? 0)*100)}% complete</strong></div><div className="settings-tag-list">{state.data.company.objects.map((item) => <span key={item.id}>{item.name}<small>{item.object_type.replaceAll("_", " ")}</small></span>)}</div>{!state.data.company.objects.length && <EmptySettings text="No company products, dependencies, or competitors are configured." action="Complete context" href="/onboarding" />}</SettingsPanel>}
        {tab === "Alerts & Digests" && <SettingsPanel title="Alerts & Digests" description="Choose what interrupts you and how summaries are delivered."><form className="preferences-form" onSubmit={saveAlerts}><fieldset><legend>Domains</legend>{alertDomains.map(([value,label]) => <label key={value}><input defaultChecked={state.data.alerts.domain_codes.includes(value)} name="domain" type="checkbox" value={value}/><span>{label}</span></label>)}</fieldset><fieldset><legend>Urgency</legend>{["CRITICAL","HIGH","MEDIUM"].map((item) => <label key={item}><input defaultChecked={state.data.alerts.urgency_bands.includes(item)} name="urgency" type="checkbox" value={item}/><span>{item}</span></label>)}</fieldset><fieldset><legend>Channels</legend>{[["IN_APP","In app"],["EMAIL","Email"]].map(([value,label]) => <label key={value}><input defaultChecked={state.data.alerts.delivery_channels.includes(value)} name="channel" type="checkbox" value={value}/><span>{label}</span></label>)}</fieldset><label className="select-field"><span>Digest frequency</span><select defaultValue={state.data.alerts.digest_frequency} name="digest"><option value="DAILY">Daily</option><option value="WEEKLY">Weekly</option><option value="NONE">None</option></select></label><button className="primary-button" type="submit">Save preferences</button>{message && <p className="form-message">{message}</p>}</form></SettingsPanel>}
        {tab === "Team" && <SettingsPanel title="Team" description="Workspace membership is managed by company administrators."><div className="access-summary"><strong>{state.data.me.permission_role === "ADMIN" ? "Administrator access" : "Member access"}</strong><p>Team invitations and role assignment use your company workspace boundary.</p><button className="secondary-button" disabled type="button">Invite team member</button><small>Team invitations become available on Team plans.</small></div></SettingsPanel>}
        {tab === "Billing" && <SettingsPanel title="Billing" description="Review your trial, plan, and secure Paystack checkout."><div className="billing-summary"><p className="eyebrow">Current plan</p><h3>{state.data.me.plan_code}</h3><span>{state.data.me.billing_status.replaceAll("_", " ")}</span><Link className="primary-button" href="/settings/billing">View plans & billing</Link></div></SettingsPanel>}
        {tab === "API / Integrations" && <SettingsPanel title="API / Integrations" description="Connect approved data and delivery systems."><div className="integration-list"><article><strong>Stem Cogent API</strong><span>Available on plans with API access.</span><i>Plan gated</i></article><article><strong>Private company data</strong><span>Security review required before connection.</span><i>Review required</i></article></div></SettingsPanel>}
      </>}
    </div></div>
  </section></WorkspaceShell>;
}

function SettingsPanel({ title, description, children }: { title: string; description: string; children: ReactNode }) { return <section className="settings-panel"><header><h2>{title}</h2><p>{description}</p></header>{children}</section>; }
function EmptySettings({ text, action, href }: { text: string; action: string; href: string }) { return <div className="settings-empty"><p>{text}</p><Link href={href}>{action} →</Link></div>; }
