"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useCallback, useEffect, useState } from "react";

import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { DynamicTagPicker } from "@/components/ui/DynamicTagPicker";
import { apiRequest, createCheckout, getOnboardingStatus } from "@/lib/api";
import { LoadState, OnboardingStatus } from "@/lib/types";

type Me = {
  display_name: string;
  email: string;
  workspace_name: string;
  permission_role: string;
  plan_code: string;
  billing_status: string;
};

type Lens = null | {
  role_code: string;
  responsibility_tags: string[];
  priority_domains: string[];
  delivery_preference: string;
};

type Focus = { id: string; label: string; focus_type: string; weight: number }[];

type CompanyProfile = {
  profile_completeness: number;
  operating_markets: string[];
  strategic_priorities: string[];
  operating_licenses?: string[];
  clearing_rails?: string[];
  active_products?: string[];
  business_categories?: string[];
  customer_segments?: string[];
  regulatory_categories?: string[];
};

type Company = {
  profile: null | CompanyProfile;
  objects: { id: string; name: string; object_type: string }[];
  context_status: { complete: boolean; completeness: number; version: number };
};

type Alerts = {
  domain_codes: string[];
  urgency_bands: string[];
  delivery_channels: string[];
  digest_frequency: string;
  enabled: boolean;
};

type TeamMember = {
  id: string;
  email: string;
  display_name?: string;
  permission_role: string;
  status: string;
  mfa_enabled: boolean;
  last_login_at?: string;
};

type Integrations = {
  plan_code: string;
  api_enabled: boolean;
  private_uploads: boolean | number;
  api_keys: {
    id: string;
    name: string;
    key_prefix: string;
    status: string;
    last_used_at?: string;
  }[];
};

type Resource<T> = { data: T; error?: never } | { data?: never; error: string };

type SettingsData = {
  me: Me;
  lens: Resource<Lens>;
  focus: Resource<Focus>;
  company: Resource<Company>;
  alerts: Resource<Alerts>;
  team: Resource<TeamMember[] | null>;
  integrations: Resource<Integrations>;
};

const tabs = [
  "Profile",
  "Operational Baseline & Rails",
  "Decision Lens",
  "Focus Areas",
  "Company Context",
  "Alerts & Digests",
  "Team",
  "Billing",
  "API / Integrations",
] as const;

const STANDARD_LICENSES = [
  { id: "PSSP", label: "PSSP", desc: "Payment Solutions Service Provider" },
  { id: "MMO", label: "MMO", desc: "Mobile Money Operator" },
  { id: "Switching", label: "Switching", desc: "Switching & Processing" },
  { id: "IMTO", label: "IMTO", desc: "Int'l Money Transfer Operator" },
  { id: "Super-Agent", label: "Super-Agent", desc: "Agency Banking Network" },
  { id: "MFB", label: "MFB", desc: "Microfinance Bank" },
  { id: "Applying/None", label: "Applying / None", desc: "In Progress / Fintech Partner" },
];

const STANDARD_RAILS = [
  { id: "NIBSS", label: "NIBSS Instant Payment (NIP)", desc: "National Central Switch" },
  { id: "Providus", label: "Providus Bank Core", desc: "Virtual Acct / Direct Inflow" },
  { id: "Wema", label: "Wema / ALAT Rails", desc: "Tier-1 Agency / Virtual Acct" },
  { id: "Interswitch", label: "Interswitch Verve/Switch", desc: "Card Routing & Clearing" },
  { id: "Paystack", label: "Paystack Core", desc: "Merchant Gateway" },
  { id: "Flutterwave", label: "Flutterwave Direct", desc: "Pan-African Multi-Currency" },
];

const STANDARD_PRODUCTS = [
  { id: "Virtual Accounts", label: "Virtual Accounts & Inflows" },
  { id: "Card Issuance", label: "Card Issuance (Verve/Visa/MC)" },
  { id: "POS Acquiring", label: "POS Acquiring & Terminals" },
  { id: "Cross-Border Trade", label: "Cross-Border FX & Remittance" },
  { id: "P2P", label: "P2P & Consumer Wallets" },
];

const alertDomains = [
  ["REGULATORY_POLICY", "Regulatory"],
  ["COMPETITIVE_PRODUCT", "Competitive product"],
  ["INFRASTRUCTURE_RELIABILITY", "Infrastructure"],
  ["CUSTOMER_MARKET", "Customer & market"],
  ["FINANCIAL_ECONOMIC", "Financial & economic"],
  ["CAPITAL_PARTNERSHIP", "Capital & partnership"],
  ["MARKET_EXPANSION", "Market expansion"],
  ["FRAUD_RISK_TRUST", "Fraud, risk & trust"],
] as const;

function permissionLabel(role: string) {
  return role === "ADMIN" ? "Workspace administrator" : role.replaceAll("_", " ");
}

async function resource<T>(request: Promise<T>): Promise<Resource<T>> {
  try {
    return { data: await request };
  } catch (error) {
    return {
      error:
        error instanceof Error
          ? error.message
          : "This settings section could not be loaded.",
    };
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
        me.permission_role === "ADMIN"
          ? resource(apiRequest<TeamMember[]>("/api/v1/team"))
          : Promise.resolve<Resource<null>>({ data: null }),
        resource(apiRequest<Integrations>("/api/v1/integrations")),
      ]);
      setState({
        status: "ready",
        data: { me, lens, focus, company, alerts, team, integrations },
      });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Settings could not be loaded.",
      });
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
      await apiRequest("/api/v1/alert-preferences", {
        method: "PUT",
        body: JSON.stringify({
          domain_codes: form.getAll("domain"),
          urgency_bands: form.getAll("urgency"),
          delivery_channels: form.getAll("channel"),
          minimum_relevance_band: null,
          digest_frequency: form.get("digest"),
          enabled: true,
        }),
      });
      setMessage("Alert and digest preferences saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Preferences could not be saved.");
    } finally {
      setSavingAlerts(false);
    }
  }

  return (
    <WorkspaceShell>
      <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 font-sans">
        {/* Enterprise Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200">
                Workspace Controls
              </span>
            </div>
            <h1 className="text-3xl font-black tracking-tight text-slate-900 mt-1">
              Settings & Customization
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Manage your operational baseline, clearing rails, relevance lenses, team seats, and enterprise plan.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/settings/policies"
              className="text-xs font-bold text-slate-700 hover:text-slate-900 bg-white border border-slate-300 hover:border-slate-400 px-3.5 py-2 rounded-lg shadow-2xs transition"
            >
              Policy Governance Vault →
            </Link>
          </div>
        </div>

        {/* Full-Width Grid: Left Nav (3 cols) + Right Content (9 cols) */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
          {/* Navigation Tabs */}
          <nav
            aria-label="Settings sections"
            className="md:col-span-3 bg-white border border-slate-200 rounded-2xl p-2.5 shadow-xs space-y-1 sticky md:top-20"
          >
            {tabs.map((item) => {
              const active = tab === item;
              return (
                <button
                  key={item}
                  type="button"
                  aria-current={active ? "page" : undefined}
                  onClick={() => setTab(item)}
                  className={`w-full text-left px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-between cursor-pointer ${
                    active
                      ? "bg-slate-900 text-white shadow-xs"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  <span>{item}</span>
                  {active && <span className="text-blue-400 font-mono text-[10px]">●</span>}
                </button>
              );
            })}
          </nav>

          {/* Active Settings Panel */}
          <div className="md:col-span-9 bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xs min-h-[500px]">
            {state.status === "loading" && <ModuleLoading label="Loading settings" />}
            {state.status === "error" && (
              <ModuleFailure message={state.message} retry={() => void load()} />
            )}
            {state.status === "ready" && (
              <>
                {/* 1. Profile */}
                {tab === "Profile" && (
                  <SettingsPanel
                    title="Profile & Workspace Access"
                    description="Your corporate identity and organization access permissions."
                  >
                    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                        <dt className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                          Full Name
                        </dt>
                        <dd className="text-sm font-black text-slate-900 mt-1">
                          {state.data.me.display_name}
                        </dd>
                      </div>
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                        <dt className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                          Corporate Email
                        </dt>
                        <dd className="text-sm font-black text-slate-900 mt-1 font-mono">
                          {state.data.me.email}
                        </dd>
                      </div>
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                        <dt className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                          Tenant Organization
                        </dt>
                        <dd className="text-sm font-black text-slate-900 mt-1">
                          {state.data.me.workspace_name}
                        </dd>
                      </div>
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                        <dt className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                          Workspace Permission Role
                        </dt>
                        <dd className="text-sm font-black text-blue-700 mt-1 uppercase">
                          {permissionLabel(state.data.me.permission_role)}
                        </dd>
                      </div>
                    </dl>
                  </SettingsPanel>
                )}

                {/* 2. Operational Baseline & Rails (DynamicTagPicker Integration) */}
                {tab === "Operational Baseline & Rails" && (
                  <ResourcePanel resource={state.data.company} retry={load}>
                    {(company) => (
                      <OperationalBaselinePanel
                        company={company}
                        onSaveSuccess={load}
                      />
                    )}
                  </ResourcePanel>
                )}

                {/* 3. Decision Lens */}
                {tab === "Decision Lens" && (
                  <ResourcePanel resource={state.data.lens} retry={load}>
                    {(lens) => (
                      <SettingsPanel
                        title="Decision Lens Calibration"
                        description="Controls how Decision Briefs are ranked and synthesized for your executive role."
                      >
                        {lens ? (
                          <div className="space-y-4 pt-2">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                                <span className="text-[10px] font-bold uppercase text-slate-400 block">
                                  Calibrated Role
                                </span>
                                <span className="text-base font-bold text-slate-900">
                                  {lens.role_code.replaceAll("_", " ")}
                                </span>
                              </div>
                              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                                <span className="text-[10px] font-bold uppercase text-slate-400 block">
                                  Delivery Preference
                                </span>
                                <span className="text-base font-bold text-slate-900">
                                  {lens.delivery_preference.replaceAll("_", " ")}
                                </span>
                              </div>
                            </div>
                            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                              <span className="text-[10px] font-bold uppercase text-slate-400 block">
                                Priority Domains
                              </span>
                              <div className="flex flex-wrap gap-1.5">
                                {lens.priority_domains.map((dom) => (
                                  <span
                                    key={dom}
                                    className="px-2.5 py-1 rounded-md text-xs font-semibold bg-white border border-slate-200 text-slate-800"
                                  >
                                    {dom}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        ) : (
                          <EmptySettings
                            text="Your Decision Lens is not configured."
                            action="Configure now"
                            href="/onboarding/stage-b"
                          />
                        )}
                      </SettingsPanel>
                    )}
                  </ResourcePanel>
                )}

                {/* 4. Focus Areas */}
                {tab === "Focus Areas" && (
                  <ResourcePanel resource={state.data.focus} retry={load}>
                    {(focus) => (
                      <SettingsPanel
                        title="Focus Areas & Priority Tags"
                        description="High-priority vigilance topics that boost signal matching relevance."
                      >
                        {focus.length ? (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                            {focus.map((item) => (
                              <div
                                key={item.id}
                                className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between"
                              >
                                <div>
                                  <span className="font-bold text-xs text-slate-900 block">
                                    {item.label}
                                  </span>
                                  <span className="text-[10px] text-slate-500 font-mono">
                                    {item.focus_type.replaceAll("_", " ")}
                                  </span>
                                </div>
                                <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                                  Weight: {item.weight}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <EmptySettings
                            text="No personal Focus Areas are active."
                            action="Configure in Stage B"
                            href="/onboarding/stage-b"
                          />
                        )}
                      </SettingsPanel>
                    )}
                  </ResourcePanel>
                )}

                {/* 5. Company Context */}
                {tab === "Company Context" && (
                  <ResourcePanel resource={state.data.company} retry={load}>
                    {(company) => (
                      <SettingsPanel
                        title="Company Context Architecture"
                        description={`Shared business context used for company-specific relevance · version ${company.context_status.version}.`}
                      >
                        <div className="space-y-4 pt-2">
                          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                            <div>
                              <span className="text-xs font-bold text-slate-900 block">
                                Context Completeness
                              </span>
                              <span className="text-[11px] text-slate-500">
                                High completeness improves signal accuracy
                              </span>
                            </div>
                            <span className="text-lg font-black text-blue-700 font-mono">
                              {Math.round(company.context_status.completeness * 100)}%
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {company.objects.map((item) => (
                              <span
                                key={item.id}
                                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200 flex items-center gap-1.5"
                              >
                                <span>{item.name}</span>
                                <small className="text-[9px] uppercase tracking-wider text-slate-500 font-mono">
                                  {item.object_type.replaceAll("_", " ")}
                                </small>
                              </span>
                            ))}
                          </div>
                        </div>
                      </SettingsPanel>
                    )}
                  </ResourcePanel>
                )}

                {/* 6. Alerts & Digests */}
                {tab === "Alerts & Digests" && (
                  <ResourcePanel resource={state.data.alerts} retry={load}>
                    {(alerts) => (
                      <SettingsPanel
                        title="Alerts & Notification Thresholds"
                        description="Choose what triggers notification digests and instant delivery channels."
                      >
                        <form className="space-y-6 pt-2" onSubmit={saveAlerts}>
                          <div className="space-y-2">
                            <span className="text-xs font-bold uppercase text-slate-700 block">
                              Notification Domains
                            </span>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                              {alertDomains.map(([value, label]) => (
                                <label
                                  key={value}
                                  className="flex items-center gap-2 p-2.5 rounded-lg border border-slate-200 bg-slate-50 text-xs font-medium text-slate-700 hover:bg-slate-100 cursor-pointer"
                                >
                                  <input
                                    defaultChecked={alerts.domain_codes.includes(value)}
                                    name="domain"
                                    type="checkbox"
                                    value={value}
                                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                  />
                                  <span>{label}</span>
                                </label>
                              ))}
                            </div>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <span className="text-xs font-bold uppercase text-slate-700 block">
                                Urgency Bands
                              </span>
                              <div className="flex gap-3">
                                {["CRITICAL", "HIGH", "MEDIUM"].map((item) => (
                                  <label
                                    key={item}
                                    className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer"
                                  >
                                    <input
                                      defaultChecked={alerts.urgency_bands.includes(item)}
                                      name="urgency"
                                      type="checkbox"
                                      value={item}
                                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    <span>{item}</span>
                                  </label>
                                ))}
                              </div>
                            </div>

                            <div className="space-y-2">
                              <span className="text-xs font-bold uppercase text-slate-700 block">
                                Delivery Channels
                              </span>
                              <div className="flex gap-4">
                                {[
                                  ["IN_APP", "In-App"],
                                  ["EMAIL", "Email Notification"],
                                ].map(([value, label]) => (
                                  <label
                                    key={value}
                                    className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer"
                                  >
                                    <input
                                      defaultChecked={alerts.delivery_channels.includes(value)}
                                      name="channel"
                                      type="checkbox"
                                      value={value}
                                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    <span>{label}</span>
                                  </label>
                                ))}
                              </div>
                            </div>
                          </div>

                          <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                            <button
                              type="submit"
                              disabled={savingAlerts}
                              className="px-5 py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow-xs disabled:opacity-50 transition"
                            >
                              {savingAlerts ? "Saving…" : "Save Preferences"}
                            </button>
                            {message && (
                              <p className="text-xs text-emerald-700 font-bold">{message}</p>
                            )}
                          </div>
                        </form>
                      </SettingsPanel>
                    )}
                  </ResourcePanel>
                )}

                {/* 7. Team */}
                {tab === "Team" && (
                  <ResourcePanel resource={state.data.team} retry={load}>
                    {(team) => (
                      <TeamSettingsPanel team={team} onInviteSuccess={load} />
                    )}
                  </ResourcePanel>
                )}

                {/* 8. Billing */}
                {tab === "Billing" && (
                  <BillingSettingsPanel me={state.data.me} />
                )}

                {/* 9. API / Integrations */}
                {tab === "API / Integrations" && (
                  <ResourcePanel resource={state.data.integrations} retry={load}>
                    {(integrations) => (
                      <SettingsPanel
                        title="API & Sovereign Integrations"
                        description="Connection keys and private tenant uploads."
                      >
                        <div className="space-y-4 pt-2">
                          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
                            <div>
                              <strong className="text-xs font-bold text-slate-900 block">
                                Stem Cogent API
                              </strong>
                              <span className="text-[11px] text-slate-500">
                                {integrations.api_enabled
                                  ? `${integrations.api_keys.length} active API key${
                                      integrations.api_keys.length === 1 ? "" : "s"
                                    }`
                                  : `Gated on ${integrations.plan_code}`}
                              </span>
                            </div>
                            <span
                              className={`text-xs font-bold px-2 py-0.5 rounded ${
                                integrations.api_enabled
                                  ? "bg-emerald-50 text-emerald-700"
                                  : "bg-slate-200 text-slate-600"
                              }`}
                            >
                              {integrations.api_enabled ? "Enabled" : "Plan Gated"}
                            </span>
                          </div>
                          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
                            <div>
                              <strong className="text-xs font-bold text-slate-900 block">
                                Private Company Data Feeds
                              </strong>
                              <span className="text-[11px] text-slate-500">
                                Managed telemetry ingest pipeline with Stem Systems Ltd
                              </span>
                            </div>
                            <span className="text-xs font-bold px-2 py-0.5 rounded bg-slate-200 text-slate-600">
                              Pilot Managed
                            </span>
                          </div>
                        </div>
                      </SettingsPanel>
                    )}
                  </ResourcePanel>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </WorkspaceShell>
  );
}

function OperationalBaselinePanel({
  company,
  onSaveSuccess,
}: {
  company: Company;
  onSaveSuccess: () => Promise<void>;
}) {
  const profile = company.profile;

  const [licenses, setLicenses] = useState<string[]>(
    profile?.operating_licenses && profile.operating_licenses.length > 0
      ? profile.operating_licenses
      : ["PSSP"]
  );
  const [rails, setRails] = useState<string[]>(
    profile?.clearing_rails && profile.clearing_rails.length > 0
      ? profile.clearing_rails
      : ["NIBSS", "Providus"]
  );
  const [products, setProducts] = useState<string[]>(
    profile?.active_products && profile.active_products.length > 0
      ? profile.active_products
      : ["Virtual Accounts"]
  );

  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function handleSaveBaseline(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveMessage(null);
    setSaveError(null);

    try {
      await apiRequest("/api/v1/context/company", {
        method: "PUT",
        body: JSON.stringify({
          operating_licenses: licenses,
          clearing_rails: rails,
          active_products: products,
          operating_markets: profile?.operating_markets || ["NG"],
          strategic_priorities: profile?.strategic_priorities || [],
          business_categories: profile?.business_categories || [],
          customer_segments: profile?.customer_segments || [],
          regulatory_categories: profile?.regulatory_categories || [],
          compliance_thresholds: {},
        }),
      });
      setSaveMessage("Operational baseline and rails updated successfully.");
      await onSaveSuccess();
    } catch (err) {
      setSaveError(
        err instanceof Error ? err.message : "Failed to update operational baseline."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <SettingsPanel
      title="Operational Baseline, Licenses & Clearing Rails"
      description="Expand licenses and partner clearing rails using dynamic custom tags as operations scale."
    >
      <form onSubmit={handleSaveBaseline} className="space-y-8 pt-4">
        {saveMessage && (
          <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-bold flex items-center gap-2">
            <span>✓</span>
            <span>{saveMessage}</span>
          </div>
        )}
        {saveError && (
          <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-bold">
            {saveError}
          </div>
        )}

        {/* Operating Licenses */}
        <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-4">
          <DynamicTagPicker
            id="settings-licenses-picker"
            label="Operating Licenses Held or Partnered"
            description="Select standard licenses or click + Add Custom (e.g. SEC Digital Asset VASP, Finance Co.)"
            standardOptions={STANDARD_LICENSES}
            selected={licenses}
            onChange={setLicenses}
            customPlaceholder="e.g. SEC Digital Asset VASP, Finance Company"
            categoryName="license"
          />
        </div>

        {/* Clearing Rails & Partner Banks */}
        <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-4">
          <DynamicTagPicker
            id="settings-rails-picker"
            label="Active Clearing Rails & Partner Settlement Banks"
            description="Select standard rails or click + Add Custom (e.g. Kora RMB Rail, VFD Microfinance)"
            standardOptions={STANDARD_RAILS}
            selected={rails}
            onChange={setRails}
            customPlaceholder="e.g. Kora RMB Rail, VFD Partner Rails"
            categoryName="rail"
          />
        </div>

        {/* Active Product Verticals */}
        <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-4">
          <DynamicTagPicker
            id="settings-products-picker"
            label="Active Product Verticals & Commercial Corridors"
            description="Add custom verticals to calibrate targeted threat intelligence"
            standardOptions={STANDARD_PRODUCTS}
            selected={products}
            onChange={setProducts}
            customPlaceholder="e.g. Agency Banking Super-Node, Payroll Remittance"
            categoryName="product"
          />
        </div>

        <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
          <span className="text-xs text-slate-500 font-medium">
            Changes immediately update background relevance weighting and radar feeds.
          </span>
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow-xs disabled:opacity-50 transition cursor-pointer"
          >
            {saving ? "Saving Footprint…" : "Save Baseline & Rails →"}
          </button>
        </div>
      </form>
    </SettingsPanel>
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
  const [assignedLens, setAssignedLens] = useState<
    "executive_strategy" | "compliance_legal" | "product_engineering" | "treasury_reconciliation"
  >("executive_strategy");
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
      setInviteError(
        err instanceof Error ? err.message : "Failed to generate teammate invitation."
      );
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
            className="h-10 px-4 rounded-lg bg-blue-600 text-white text-xs font-bold hover:bg-blue-700 active:scale-95 transition shadow-2xs flex items-center justify-center gap-1.5 disabled:opacity-50 cursor-pointer"
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
                <span className="text-[10px] text-slate-500 block uppercase">
                  6-Digit Verification OTP
                </span>
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
                  className="px-2 py-1 rounded bg-slate-100 text-[11px] font-bold text-slate-700 hover:bg-slate-200 cursor-pointer"
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
        <div className="p-4 rounded-xl border border-dashed border-slate-300 text-center text-xs text-slate-500">
          <p>No other teammates invited yet. Use the invite generator above to add members.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {team.map((member) => (
            <article
              key={member.id}
              className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-white shadow-2xs"
            >
              <div>
                <strong className="text-xs font-bold text-slate-900 block">
                  {member.display_name || member.email}
                </strong>
                <span className="block text-[11px] text-slate-500 font-mono">
                  {member.email}
                </span>
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
      setCheckoutError(
        err instanceof Error ? err.message : "Failed to initialize Paystack checkout."
      );
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
            <span className="text-xl font-black text-blue-950">
              {pilotDaysRemaining} / 14
            </span>
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
            Status:{" "}
            <strong className="text-emerald-700 uppercase">
              {me.billing_status.replaceAll("_", " ")}
            </strong>
          </p>
          <div className="pt-2 border-t border-slate-100 text-xs text-slate-500 font-mono">
            Monthly Queries: {onboardingStatus?.queries_used_this_period || 0} /{" "}
            {onboardingStatus?.monthly_workspace_query_limit || 500}
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
            className="w-full h-10 rounded-lg bg-blue-600 text-white font-bold text-xs hover:bg-blue-500 active:scale-95 transition flex items-center justify-center gap-2 shadow-sm disabled:opacity-50 cursor-pointer"
          >
            {isCheckingOut ? "Connecting to Paystack..." : "Upgrade to Growth Tier via Paystack →"}
          </button>
        </div>
      </div>
    </SettingsPanel>
  );
}

function ResourcePanel<T>({
  resource: value,
  retry,
  children,
}: {
  resource: Resource<T>;
  retry: () => Promise<void>;
  children: (data: T) => ReactNode;
}) {
  if ("error" in value)
    return <ModuleFailure message={value.error} retry={() => void retry()} />;
  return <>{children(value.data)}</>;
}

function SettingsPanel({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <header className="pb-4 border-b border-slate-100">
        <h2 className="text-lg font-black text-slate-900 tracking-tight">{title}</h2>
        <p className="text-xs text-slate-500 mt-0.5">{description}</p>
      </header>
      {children}
    </section>
  );
}

function EmptySettings({ text, action, href }: { text: string; action: string; href: string }) {
  return (
    <div className="p-8 rounded-xl border border-dashed border-slate-300 text-center space-y-2">
      <p className="text-xs text-slate-600">{text}</p>
      <Link
        href={href}
        className="inline-block text-xs font-bold text-blue-600 hover:text-blue-700 underline"
      >
        {action} →
      </Link>
    </div>
  );
}
