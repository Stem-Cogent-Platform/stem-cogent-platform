"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { StemMark } from "@/components/stem-mark";
import {
  bootstrapSession,
  getOnboardingStatus,
  submitStageA,
  submitStageB,
} from "@/lib/api";

const AVAILABLE_LICENSES = [
  { id: "PSSP", label: "PSSP", desc: "Payment Solution Service Provider" },
  { id: "MMO", label: "MMO", desc: "Mobile Money Operator" },
  { id: "MFB", label: "MFB", desc: "Tier-1 / Tier-2 Microfinance Bank" },
  { id: "Switching & Processing", label: "Switching & Processing", desc: "Full Transaction Switch" },
  { id: "IMTO", label: "IMTO", desc: "Cross-Border Remittance" },
  { id: "Super Agent", label: "Super Agent", desc: "Agency Banking Network" },
  { id: "Payment Gateway", label: "Payment Gateway", desc: "Online Merchant Acquiring" },
];

const AVAILABLE_RAILS = [
  { id: "Providus Bank Core", label: "Providus Bank Core", type: "Settlement Partner" },
  { id: "NIBSS Instant Payment (NIP)", label: "NIBSS (NIP)", type: "National Clearing Switch" },
  { id: "Wema ALAT Direct", label: "Wema ALAT", type: "Virtual Account Rail" },
  { id: "Interswitch Core Switch", label: "Interswitch", type: "Card & Switching Rail" },
  { id: "Zenith Bank Direct", label: "Zenith Direct", type: "Commercial Bank Clearing" },
  { id: "Sterling Bank Switch", label: "Sterling Bank", type: "Partner Core" },
];

const AVAILABLE_PRODUCTS = [
  "Virtual Accounts",
  "Direct Debit Collections",
  "Payment Gateway Checkout",
  "POS Merchant Acquiring",
  "Card Issuing Rail",
  "Cross-Border Settlement",
];

const BUSINESS_FUNCTIONS = [
  { id: "EXECUTIVE_STRATEGY", label: "Executive Strategy", desc: "Founder / CEO / Board: Strategic bets & capital allocation" },
  { id: "COMPLIANCE_LEGAL", label: "Compliance & Legal", desc: "Regulatory liaison, CBN circular compliance, and audit defense" },
  { id: "PRODUCT_ENGINEERING", label: "Product & Engineering", desc: "APIs, checkout latency, failover routing, and switch uptime" },
  { id: "TREASURY_RECONCILIATION", label: "Treasury & Settlement", desc: "Float reconciliation, interchange spreads, and clearing queues" },
];

type DecisionLensType = "executive_strategy" | "compliance_legal" | "product_engineering" | "treasury_reconciliation";

export function OnboardingWizard() {
  const router = useRouter();

  // Wizard state: "loading" | "stage_a" | "bootstrapping" | "stage_b" | "completing"
  const [stage, setStage] = useState<"loading" | "stage_a" | "bootstrapping" | "stage_b" | "completing">("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Stage A Fields
  const [companyName, setCompanyName] = useState("");
  const [selectedLicenses, setSelectedLicenses] = useState<string[]>(["PSSP"]);
  const [selectedRails, setSelectedRails] = useState<string[]>(["Providus Bank Core", "NIBSS Instant Payment (NIP)"]);
  const [selectedProducts, setSelectedProducts] = useState<string[]>(["Virtual Accounts", "Payment Gateway Checkout"]);

  // Stage B Fields
  const [businessFunction, setBusinessFunction] = useState("EXECUTIVE_STRATEGY");
  const [decisionLens, setDecisionLens] = useState<DecisionLensType>("executive_strategy");
  const [priorityFocus, setPriorityFocus] = useState("");
  const [alertSensitivity, setAlertSensitivity] = useState<"IMPORTANT_AND_CRITICAL" | "CRITICAL_ONLY">("IMPORTANT_AND_CRITICAL");

  // Bootstrap initial status
  useEffect(() => {
    let active = true;
    async function checkStatus() {
      const ok = await bootstrapSession();
      if (!ok) {
        router.replace("/login?next=%2Fonboarding");
        return;
      }
      try {
        const status = await getOnboardingStatus();
        if (!active) return;
        if (status.organization_name) {
          setCompanyName(status.organization_name);
        }
        if (status.stage_a_completed && status.stage_b_completed) {
          router.replace("/radar");
          return;
        }
        if (status.stage_a_completed) {
          setStage("stage_b");
        } else {
          setStage("stage_a");
        }
      } catch {
        if (active) setStage("stage_a");
      }
    }
    void checkStatus();
    return () => {
      active = false;
    };
  }, [router]);

  function toggleItem(list: string[], item: string, setter: (val: string[]) => void) {
    if (list.includes(item)) {
      if (list.length > 1) {
        setter(list.filter((x) => x !== item));
      }
    } else {
      setter([...list, item]);
    }
  }

  async function handleStageASubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!companyName.trim()) {
      setErrorMessage("Please enter your organization or fintech name.");
      return;
    }
    setErrorMessage(null);
    setStage("bootstrapping");

    try {
      await submitStageA({
        company_name: companyName.trim(),
        operating_licenses: selectedLicenses,
        active_products: selectedProducts,
        clearing_rails: selectedRails,
        primary_country: "NG",
        compliance_thresholds: {},
      });

      // Brief visual pause to show bootstrap progress
      setTimeout(() => {
        setStage("stage_b");
      }, 1000);
    } catch (err) {
      setStage("stage_a");
      setErrorMessage(err instanceof Error ? err.message : "Failed to save operational profile.");
    }
  }

  async function handleStageBSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMessage(null);
    setStage("completing");

    try {
      await submitStageB({
        business_function: businessFunction,
        decision_lens: decisionLens,
        priority_focus: priorityFocus.trim() || undefined,
        alert_sensitivity: alertSensitivity,
      });

      // Smooth transition into Radar
      setTimeout(() => {
        router.replace("/radar");
      }, 600);
    } catch (err) {
      setStage("stage_b");
      setErrorMessage(err instanceof Error ? err.message : "Failed to save decision lens profile.");
    }
  }

  if (stage === "loading") {
    return (
      <main className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-3 border-blue-600 border-t-transparent" />
          <p className="text-sm font-semibold text-slate-700">Connecting to workspace intelligence...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 flex flex-col justify-between">
      {/* Top Header */}
      <header className="h-16 border-b border-slate-200 bg-white/90 backdrop-blur-md px-6 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <StemMark compact />
          <span className="font-extrabold tracking-tight text-slate-900 text-lg">Stem Cogent</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500">Step {stage === "stage_a" || stage === "bootstrapping" ? "1 of 2" : "2 of 2"}</span>
          <div className="w-20 h-1.5 rounded-full bg-slate-100 overflow-hidden border border-slate-200">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: stage === "stage_a" || stage === "bootstrapping" ? "50%" : "100%" }}
            />
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-2xl bg-white border border-slate-200 rounded-2xl p-6 sm:p-10 shadow-[0_4px_12px_rgba(0,0,0,0.06)]">
          {errorMessage && (
            <div className="mb-6 rounded-xl bg-red-50 p-4 border border-red-200 text-xs text-red-700 font-medium">
              {errorMessage}
            </div>
          )}

          {/* STAGE A: COMPANY SETUP */}
          {(stage === "stage_a" || stage === "bootstrapping") && (
            <form onSubmit={handleStageASubmit} className="space-y-6">
              <div>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200 mb-2">
                  Stage A · Company Operational Footprint
                </span>
                <h1 className="text-2xl font-black tracking-tight text-slate-900">
                  Configure Your Operational Rail & Licensing Profile
                </h1>
                <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
                  Stem uses your active regulatory licenses and partner bank corridors to immediately compute direct statutory exposures, margin threats, and rail stress.
                </p>
              </div>

              {/* Organization Name */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                  Fintech / Company Name
                </label>
                <input
                  type="text"
                  required
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g. Kuda, Moniepoint, Flutterwave, Paystack"
                  className="w-full h-11 px-3.5 rounded-xl border border-slate-300 text-sm focus:border-blue-600 focus:outline-none transition shadow-2xs font-medium"
                />
              </div>

              {/* Multi-Select Licenses */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                  Operating Licenses & Authorizations (Multi-Select)
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {AVAILABLE_LICENSES.map((lic) => {
                    const active = selectedLicenses.includes(lic.id);
                    return (
                      <button
                        key={lic.id}
                        type="button"
                        onClick={() => toggleItem(selectedLicenses, lic.id, setSelectedLicenses)}
                        className={`p-2.5 rounded-xl text-left border transition-all ${
                          active
                            ? "border-blue-600 bg-blue-50 text-blue-900 shadow-2xs"
                            : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold">{lic.label}</span>
                          {active && <span className="text-blue-600 font-bold text-xs">✓</span>}
                        </div>
                        <span className="text-[10px] text-slate-500 block truncate mt-0.5">{lic.desc}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Multi-Select Rails */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                  Active Clearing Rails & Partner Banks (Multi-Select)
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {AVAILABLE_RAILS.map((rail) => {
                    const active = selectedRails.includes(rail.id);
                    return (
                      <button
                        key={rail.id}
                        type="button"
                        onClick={() => toggleItem(selectedRails, rail.id, setSelectedRails)}
                        className={`p-2.5 rounded-xl text-left border transition-all ${
                          active
                            ? "border-blue-600 bg-blue-50 text-blue-900 shadow-2xs"
                            : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold">{rail.label}</span>
                          {active && <span className="text-blue-600 font-bold text-xs">✓</span>}
                        </div>
                        <span className="text-[10px] text-slate-500 block truncate mt-0.5">{rail.type}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Active Products Pills */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                  Core Active Product Lines
                </label>
                <div className="flex flex-wrap gap-2">
                  {AVAILABLE_PRODUCTS.map((prod) => {
                    const active = selectedProducts.includes(prod);
                    return (
                      <button
                        key={prod}
                        type="button"
                        onClick={() => toggleItem(selectedProducts, prod, setSelectedProducts)}
                        className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
                          active
                            ? "border-blue-600 bg-blue-600 text-white"
                            : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                        }`}
                      >
                        {active ? `✓ ${prod}` : `+ ${prod}`}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Submit Action */}
              <button
                type="submit"
                disabled={stage === "bootstrapping"}
                className="w-full h-12 rounded-xl bg-blue-600 text-white font-bold text-sm shadow-sm hover:bg-blue-700 active:scale-[0.99] transition disabled:opacity-75 flex items-center justify-center gap-2"
              >
                {stage === "bootstrapping" ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <span>Bootstrapping ecosystem intelligence...</span>
                  </>
                ) : (
                  <>
                    <span>Save Operational Profile & Continue</span>
                    <span>→</span>
                  </>
                )}
              </button>
            </form>
          )}

          {/* STAGE B: PERSONAL LENS SETUP */}
          {(stage === "stage_b" || stage === "completing") && (
            <form onSubmit={handleStageBSubmit} className="space-y-6">
              <div>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 mb-2">
                  Stage B · Personal Executive Lens
                </span>
                <h1 className="text-2xl font-black tracking-tight text-slate-900">
                  Calibrate Your Executive Radar & Decision Prioritization
                </h1>
                <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
                  Customize the AI agent synthesis and alert thresholds to match your specific accountability and risk sensitivity.
                </p>
              </div>

              {/* Question 1: Business Function */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                  1. What is your primary business function?
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {BUSINESS_FUNCTIONS.map((fn) => {
                    const active = businessFunction === fn.id;
                    return (
                      <button
                        key={fn.id}
                        type="button"
                        onClick={() => {
                          setBusinessFunction(fn.id);
                          // Auto align lens
                          const map: Record<string, DecisionLensType> = {
                            EXECUTIVE_STRATEGY: "executive_strategy",
                            COMPLIANCE_LEGAL: "compliance_legal",
                            PRODUCT_ENGINEERING: "product_engineering",
                            TREASURY_RECONCILIATION: "treasury_reconciliation",
                          };
                          if (map[fn.id]) setDecisionLens(map[fn.id]);
                        }}
                        className={`p-3 rounded-xl text-left border transition ${
                          active
                            ? "border-blue-600 bg-blue-50 text-blue-900 shadow-2xs"
                            : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                        }`}
                      >
                        <div className="font-bold text-xs">{fn.label}</div>
                        <div className="text-[11px] text-slate-500 mt-1 leading-snug">{fn.desc}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Question 2: Decision Lens */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                  2. Select your dominant Decision Lens
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: "executive_strategy", label: "Executive Strategy", desc: "M&A, licenses, commercial threats" },
                    { id: "compliance_legal", label: "Compliance & Legal", desc: "Circulars, penalties, regulatory audits" },
                    { id: "product_engineering", label: "Product & Engineering", desc: "Node latency, failover, drop rates" },
                    { id: "treasury_reconciliation", label: "Treasury & Finance", desc: "Settlement float, liquidity, reserves" },
                  ].map((lens) => {
                    const active = decisionLens === lens.id;
                    return (
                      <button
                        key={lens.id}
                        type="button"
                        onClick={() => setDecisionLens(lens.id as DecisionLensType)}
                        className={`p-2.5 rounded-xl text-left border transition ${
                          active
                            ? "border-blue-600 bg-blue-50 text-blue-900 shadow-2xs"
                            : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                        }`}
                      >
                        <div className="font-bold text-xs">{lens.label}</div>
                        <div className="text-[10px] text-slate-500 mt-0.5 truncate">{lens.desc}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Priority Domain Focus (Optional) */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                  Specific Strategic Focus (Optional)
                </label>
                <input
                  type="text"
                  value={priorityFocus}
                  onChange={(e) => setPriorityFocus(e.target.value)}
                  placeholder="e.g. Cross-border FX spreads, CBN merchant KYC circulars, NIP inward stability"
                  className="w-full h-11 px-3.5 rounded-xl border border-slate-300 text-sm focus:border-blue-600 focus:outline-none transition shadow-2xs font-medium"
                />
              </div>

              {/* Question 3: Notification Sensitivity */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                  3. Alert Notification Sensitivity
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <button
                    type="button"
                    onClick={() => setAlertSensitivity("IMPORTANT_AND_CRITICAL")}
                    className={`p-3 rounded-xl text-left border transition ${
                      alertSensitivity === "IMPORTANT_AND_CRITICAL"
                        ? "border-blue-600 bg-blue-50 text-blue-900 shadow-2xs"
                        : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                    }`}
                  >
                    <div className="font-bold text-xs">Important & Critical (Recommended)</div>
                    <div className="text-[11px] text-slate-500 mt-1">
                      Deliver real-time telemetry drops, statutory circular deadlines, and competitive price wars.
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setAlertSensitivity("CRITICAL_ONLY")}
                    className={`p-3 rounded-xl text-left border transition ${
                      alertSensitivity === "CRITICAL_ONLY"
                        ? "border-blue-600 bg-blue-50 text-blue-900 shadow-2xs"
                        : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                    }`}
                  >
                    <div className="font-bold text-xs">Critical Emergency Only</div>
                    <div className="text-[11px] text-slate-500 mt-1">
                      Only page when active rail outages exceed 15 minutes or immediate fines apply.
                    </div>
                  </button>
                </div>
              </div>

              {/* Submit Action */}
              <button
                type="submit"
                disabled={stage === "completing"}
                className="w-full h-12 rounded-xl bg-emerald-600 text-white font-bold text-sm shadow-sm hover:bg-emerald-700 active:scale-[0.99] transition disabled:opacity-75 flex items-center justify-center gap-2"
              >
                {stage === "completing" ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <span>Launching Executive Radar...</span>
                  </>
                ) : (
                  <>
                    <span>Complete Setup & Launch Radar Feed</span>
                    <span>→</span>
                  </>
                )}
              </button>
            </form>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="h-12 border-t border-slate-200 bg-white text-center flex items-center justify-center text-xs text-slate-500 font-medium">
        Stem Cogent Decision Intelligence Platform · Grounded on Central Bank of Nigeria Gazettes & Switch Telemetry
      </footer>
    </main>
  );
}
