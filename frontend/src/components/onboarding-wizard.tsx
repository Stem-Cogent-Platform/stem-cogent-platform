"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { apiRequest, bootstrapSession } from "@/lib/api";

const steps = ["Company", "Company Context", "Your Role", "Decision Lens", "Focus Areas", "Delivery"];
const roles = [
  ["CEO", "Founder / CEO", "Company direction, capital and major trade-offs"],
  ["CSO", "CSO / Strategy", "Market moves, competition and strategic choices"],
  ["COO", "COO / Operations", "Reliability, dependencies and execution"],
  ["CFO", "CFO / Finance", "Revenue, margin, capital and financial exposure"],
  ["PRODUCT", "Product", "Product impact, roadmap and customer needs"],
  ["GROWTH", "Growth", "Acquisition, expansion and market movement"],
  ["COMPLIANCE_RISK", "Compliance / Risk", "Regulation, controls and obligations"],
  ["RESEARCH", "Research", "Evidence, patterns and market intelligence"],
  ["OTHER", "Other", "Configure priorities around your responsibilities"]
] as const;
const domains = ["REGULATORY_POLICY", "INFRASTRUCTURE_RELIABILITY", "COMPETITIVE_PRODUCT", "MARKET_EXPANSION", "FINANCIAL_ECONOMIC", "FRAUD_RISK_TRUST", "CUSTOMER_MARKET"];
const domainLabels: Record<string, string> = { REGULATORY_POLICY: "Regulatory policy", INFRASTRUCTURE_RELIABILITY: "Infrastructure reliability", COMPETITIVE_PRODUCT: "Competitive product", MARKET_EXPANSION: "Market expansion", FINANCIAL_ECONOMIC: "Financial & economic", FRAUD_RISK_TRUST: "Security, fraud & trust", CUSTOMER_MARKET: "Customer & market" };
const marketLabels: Record<string, string> = { NG: "Nigeria", GH: "Ghana", KE: "Kenya", ZA: "South Africa", GB: "United Kingdom", OTHER: "Other" };
const deliveries = [
  ["CRITICAL_ONLY", "Critical only", "Only developments that require immediate review"],
  ["IMPORTANT_AND_CRITICAL", "Important + Critical", "Recommended for active decision owners"],
  ["DAILY_BRIEFING", "Daily Briefing", "One structured briefing each workday"],
  ["WEEKLY_BRIEFING", "Weekly Briefing", "A consolidated weekly decision view"]
] as const;

function list(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

export function OnboardingWizard() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [sessionReady, setSessionReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [state, setState] = useState({
    categories: [] as string[], markets: ["NG"] as string[], segments: [] as string[],
    products: "", dependencies: "", competitors: "", regulatory: "", priorities: "",
    role: "CEO", responsibilities: "", domains: [] as string[], focus: "",
    delivery: "IMPORTANT_AND_CRITICAL"
  });
  const progress = useMemo(() => ((step + 1) / steps.length) * 100, [step]);

  useEffect(() => {
    let active = true;
    void bootstrapSession().then((authenticated) => {
      if (!active) return;
      if (!authenticated) {
        router.replace("/login?next=%2Fonboarding");
        return;
      }
      setSessionReady(true);
    });
    return () => {
      active = false;
    };
  }, [router]);

  function toggle(key: "categories" | "markets" | "segments" | "domains", value: string) {
    setState((current) => ({ ...current, [key]: current[key].includes(value) ? current[key].filter((item) => item !== value) : [...current[key], value] }));
  }

  async function finish(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      if (!(await bootstrapSession())) {
        router.replace("/login?next=%2Fonboarding");
        return;
      }
      await apiRequest("/context/company", { method: "PUT", body: JSON.stringify({
        business_categories: state.categories,
        operating_markets: state.markets,
        customer_segments: state.segments,
        regulatory_categories: list(state.regulatory),
        strategic_priorities: list(state.priorities)
      }) });
      const objects = [
        ...list(state.products).map((name) => ({ object_type: "PRODUCT", name })),
        ...list(state.dependencies).map((name) => ({ object_type: "DEPENDENCY", name, importance: "HIGH" })),
        ...list(state.competitors).map((name) => ({ object_type: "COMPETITOR", name }))
      ];
      await Promise.all(objects.map((object) => apiRequest("/context/company/objects", { method: "POST", body: JSON.stringify(object) })));
      await apiRequest("/me/decision-lens", { method: "PUT", body: JSON.stringify({
        role_code: state.role,
        responsibility_tags: list(state.responsibilities),
        priority_domains: state.domains.slice(0, 5),
        delivery_preference: state.delivery
      }) });
      await Promise.all(list(state.focus).map((label) => apiRequest("/me/focus-areas", { method: "POST", body: JSON.stringify({ focus_type: "TOPIC", label, query_text: label, weight: 1 }) })));
      router.replace("/briefing");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Your setup could not be saved. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (!sessionReady) {
    return <main className="centered-state"><p>Restoring your secure workspace sessionâ€¦</p></main>;
  }

  return (
    <form className="onboarding-wizard" onSubmit={finish}>
      <aside className="wizard-sidebar">
        <p className="eyebrow">Workspace setup</p>
        <h1>Make every brief relevant from day one.</h1>
        <p>About five minutes. You can update every choice later in Settings.</p>
        <ol>{steps.map((label, index) => <li className={index === step ? "current" : index < step ? "complete" : ""} key={label}><span>{index < step ? "✓" : index + 1}</span><strong>{label}</strong></li>)}</ol>
      </aside>
      <section className="wizard-stage">
        <div className="wizard-progress"><i style={{ width: `${progress}%` }} /></div>
        <header><span>Step {step + 1} of {steps.length}</span><button onClick={() => router.replace("/briefing")} type="button">Finish later</button></header>

        {step === 0 && <div className="wizard-panel"><p className="eyebrow">Company</p><h2>Tell us where your business operates.</h2><p>This creates the first boundary for relevant intelligence.</p><ChoiceGroup label="Fintech category" options={["Payments", "Lending", "Banking", "Infrastructure", "Insurance", "Wealth", "Commerce"]} values={state.categories} onToggle={(value) => toggle("categories", value)} /><ChoiceGroup label="Operating markets" labels={marketLabels} options={["NG", "GH", "KE", "ZA", "GB", "OTHER"]} values={state.markets} onToggle={(value) => toggle("markets", value)} /><ChoiceGroup label="Customer segments" options={["Consumers", "SMEs", "Enterprises", "Banks", "Merchants", "Developers"]} values={state.segments} onToggle={(value) => toggle("segments", value)} /></div>}
        {step === 1 && <div className="wizard-panel"><p className="eyebrow">Company Context</p><h2>What should Stem understand about the business?</h2><p>Use concise comma-separated names. Only provide information you are authorised to share.</p><div className="wizard-fields"><label><span>Products and services</span><input value={state.products} onChange={(event) => setState({ ...state, products: event.target.value })} /></label><label><span>Critical dependencies and partners</span><input value={state.dependencies} onChange={(event) => setState({ ...state, dependencies: event.target.value })} /></label><label><span>Direct competitors</span><input value={state.competitors} onChange={(event) => setState({ ...state, competitors: event.target.value })} /></label><label><span>Regulatory categories</span><input value={state.regulatory} onChange={(event) => setState({ ...state, regulatory: event.target.value })} /></label><label className="full"><span>Strategic priorities</span><input value={state.priorities} onChange={(event) => setState({ ...state, priorities: event.target.value })} /></label></div></div>}
        {step === 2 && <div className="wizard-panel"><p className="eyebrow">Your Role</p><h2>Which decisions are you responsible for?</h2><div className="role-card-grid">{roles.map(([value,label,description]) => <button className={state.role === value ? "selected" : ""} onClick={() => setState({ ...state, role: value })} type="button" key={value}><strong>{label}</strong><span>{description}</span></button>)}</div></div>}
        {step === 3 && <div className="wizard-panel"><p className="eyebrow">Decision Lens</p><h2>What do you want Stem Cogent to prioritise for you?</h2><p>Select up to five domains, then add responsibility detail.</p><ChoiceGroup label="Priority decision domains" labels={domainLabels} options={domains} values={state.domains} onToggle={(value) => state.domains.includes(value) || state.domains.length < 5 ? toggle("domains", value) : undefined} /><div className="wizard-fields single"><label><span>Your responsibilities</span><input value={state.responsibilities} onChange={(event) => setState({ ...state, responsibilities: event.target.value })} /></label></div></div>}
        {step === 4 && <div className="wizard-panel"><p className="eyebrow">Focus Areas</p><h2>What should we watch especially closely right now?</h2><p>Add competitors, regulators, infrastructure providers, markets, product categories, or active initiatives.</p><div className="wizard-fields single"><label><span>Focus areas</span><input value={state.focus} onChange={(event) => setState({ ...state, focus: event.target.value })} /></label></div><div className="focus-examples"><span>Examples</span>{["CBN circulars", "NIBSS reliability", "Merchant margin", "Cross-border payments"].map((item) => <button onClick={() => setState({ ...state, focus: state.focus ? `${state.focus}, ${item}` : item })} type="button" key={item}>+ {item}</button>)}</div></div>}
        {step === 5 && <div className="wizard-panel"><p className="eyebrow">Delivery</p><h2>How should important developments reach you?</h2><div className="delivery-list">{deliveries.map(([value,label,description]) => <button className={state.delivery === value ? "selected" : ""} onClick={() => setState({ ...state, delivery: value })} type="button" key={value}><i /> <span><strong>{label}</strong><small>{description}</small></span></button>)}</div>{message && <p className="form-message" role="alert">{message}</p>}</div>}

        <footer><button className="secondary-button" disabled={step === 0 || saving} onClick={() => setStep((value) => value - 1)} type="button">Back</button>{step < steps.length - 1 ? <button className="primary-button" disabled={(step === 0 && (!state.categories.length || !state.markets.length)) || (step === 3 && !state.domains.length)} onClick={() => setStep((value) => value + 1)} type="button">Continue</button> : <button className="primary-button" disabled={saving} type="submit">{saving ? "Creating your briefing…" : "Open my briefing"}</button>}</footer>
      </section>
    </form>
  );
}

function ChoiceGroup({ label, labels = {}, options, values, onToggle }: { label: string; labels?: Record<string, string>; options: string[]; values: string[]; onToggle: (value: string) => void }) {
  return <fieldset className="choice-group"><legend>{label}</legend><div>{options.map((option) => <button className={values.includes(option) ? "selected" : ""} onClick={() => onToggle(option)} type="button" key={option}>{values.includes(option) ? "✓ " : "+ "}{labels[option] ?? option}</button>)}</div></fieldset>;
}
