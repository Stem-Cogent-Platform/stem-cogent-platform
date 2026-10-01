"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { StemMark } from "@/components/stem-mark";
import { submitStageA, StageACompanyInput } from "@/lib/api";

interface StepMeta {
  number: number;
  id: string;
  title: string;
  subtitle: string;
}

const ONBOARDING_STEPS: StepMeta[] = [
  {
    number: 1,
    id: "company",
    title: "Company Context",
    subtitle: "Basic organizational profile",
  },
  {
    number: 2,
    id: "licenses",
    title: "Operating Licenses",
    subtitle: "Regulatory authorizations",
  },
  {
    number: 3,
    id: "rails",
    title: "Settlement Rails",
    subtitle: "Partner clearing & banks",
  },
  {
    number: 4,
    id: "products",
    title: "Product Verticals",
    subtitle: "Commercial product modules",
  },
];

interface OptionItem {
  id: string;
  title: string;
  subtitle: string;
}

const STANDARD_LICENSES: OptionItem[] = [
  { id: "PSSP", title: "PSSP", subtitle: "Payment Solutions Service Provider" },
  { id: "MMO", title: "MMO", subtitle: "Mobile Money Operator" },
  { id: "MFB", title: "MFB", subtitle: "Microfinance Bank" },
  { id: "Switching", title: "Switching", subtitle: "Switching & Processing" },
  { id: "IMTO", title: "IMTO", subtitle: "International Money Transfer Operator" },
  { id: "Super-Agent", title: "Super-Agent", subtitle: "Agency Banking Network" },
  { id: "Payment Gateway", title: "Payment Gateway", subtitle: "Online Merchant Acquiring" },
  { id: "Applying / None", title: "Applying / None", subtitle: "In Progress / Sponsor Partner" },
];

const STANDARD_RAILS: OptionItem[] = [
  { id: "NIBSS", title: "NIBSS (NIP)", subtitle: "National Central Switch" },
  { id: "PROVIDUS", title: "Providus Bank Core", subtitle: "Virtual Acct / Direct Inflow" },
  { id: "WEMA", title: "Wema ALAT Rails", subtitle: "Tier-1 Agency / Virtual Acct" },
  { id: "INTERSWITCH", title: "Interswitch Verve/Switch", subtitle: "Card Routing & Clearing" },
  { id: "PAYSTACK", title: "Paystack Core", subtitle: "Merchant & Payment Gateway" },
  { id: "FLUTTERWAVE", title: "Flutterwave Direct", subtitle: "Pan-African Multi-Currency" },
  { id: "ZENITH", title: "Zenith Direct", subtitle: "Commercial Bank Clearing" },
  { id: "STERLING", title: "Sterling Bank", subtitle: "Partner Core" },
];

const STANDARD_PRODUCTS: OptionItem[] = [
  { id: "virtual_accounts", title: "Virtual Account Issuance", subtitle: "Dynamic dedicated account generation" },
  { id: "cross_border_fx", title: "B2B Cross-Border FX", subtitle: "Import/Export trade clearing corridors" },
  { id: "pos_acquiring", title: "POS Terminal Acquiring", subtitle: "Retail merchant collection network" },
  { id: "card_issuance", title: "Card Issuance", subtitle: "Physical and virtual card infrastructure" },
  { id: "p2p_wallet", title: "P2P Mobile Wallet", subtitle: "Consumer balance & transfers" },
  { id: "api_banking", title: "API Banking / BaaS", subtitle: "Embedded finance infrastructure" },
];

export default function StageAOnboardingPage() {
  const router = useRouter();

  // Navigation State
  const [activeStep, setActiveStep] = useState<number>(1);

  // Form State
  const [companyName, setCompanyName] = useState<string>("");
  const [jurisdiction, setJurisdiction] = useState<string>("Nigeria");
  const [companySize, setCompanySize] = useState<string>("11-50");
  const [companyWebsite, setCompanyWebsite] = useState<string>("");

  const [selectedLicenses, setSelectedLicenses] = useState<string[]>(["PSSP"]);
  const [selectedRails, setSelectedRails] = useState<string[]>(["NIBSS", "PROVIDUS"]);
  const [selectedProducts, setSelectedProducts] = useState<string[]>(["virtual_accounts"]);

  // Custom Tag Input States
  const [customLicenseInput, setCustomLicenseInput] = useState<string>("");
  const [isAddingLicense, setIsAddingLicense] = useState<boolean>(false);

  const [customRailInput, setCustomRailInput] = useState<string>("");
  const [isAddingRail, setIsAddingRail] = useState<boolean>(false);

  // Submission & UI States
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [stepError, setStepError] = useState<string | null>(null);

  // Toggle selection helpers
  function toggleLicense(id: string) {
    setSelectedLicenses((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  }

  function toggleRail(id: string) {
    setSelectedRails((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  }

  function toggleProduct(id: string) {
    setSelectedProducts((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  }

  // Custom Tag Helpers
  function handleAddCustomLicense() {
    const trimmed = customLicenseInput.trim();
    if (!trimmed) {
      setIsAddingLicense(false);
      return;
    }
    const tag = trimmed.startsWith("CUSTOM:") ? trimmed : `CUSTOM: ${trimmed}`;
    if (!selectedLicenses.includes(tag)) {
      setSelectedLicenses((prev) => [...prev, tag]);
    }
    setCustomLicenseInput("");
    setIsAddingLicense(false);
  }

  function handleAddCustomRail() {
    const trimmed = customRailInput.trim();
    if (!trimmed) {
      setIsAddingRail(false);
      return;
    }
    const tag = trimmed.startsWith("CUSTOM:") ? trimmed : `CUSTOM: ${trimmed}`;
    if (!selectedRails.includes(tag)) {
      setSelectedRails((prev) => [...prev, tag]);
    }
    setCustomRailInput("");
    setIsAddingRail(false);
  }

  function removeCustomTag(tag: string, type: "license" | "rail") {
    if (type === "license") {
      setSelectedLicenses((prev) => prev.filter((item) => item !== tag));
    } else {
      setSelectedRails((prev) => prev.filter((item) => item !== tag));
    }
  }

  // Restart & Leave actions
  function handleRestart() {
    setCompanyName("");
    setJurisdiction("Nigeria");
    setCompanySize("11-50");
    setCompanyWebsite("");
    setSelectedLicenses(["PSSP"]);
    setSelectedRails(["NIBSS", "PROVIDUS"]);
    setSelectedProducts(["virtual_accounts"]);
    setCustomLicenseInput("");
    setIsAddingLicense(false);
    setCustomRailInput("");
    setIsAddingRail(false);
    setActiveStep(1);
    setStepError(null);
  }

  function handleLeave() {
    router.push("/workspace");
  }

  // Navigation handlers
  function handleNext() {
    setStepError(null);

    if (activeStep === 1) {
      if (!companyName.trim()) {
        setStepError("Company or legal entity name is required to continue.");
        return;
      }
      setActiveStep(2);
      return;
    }

    if (activeStep === 2) {
      if (selectedLicenses.length === 0) {
        setStepError("Please select at least one license or authorization (e.g. Applying / None).");
        return;
      }
      setActiveStep(3);
      return;
    }

    if (activeStep === 3) {
      if (selectedRails.length === 0) {
        setStepError("Please select at least one active settlement rail.");
        return;
      }
      setActiveStep(4);
      return;
    }
  }

  function handleBack() {
    setStepError(null);
    if (activeStep > 1) {
      setActiveStep((prev) => prev - 1);
    }
  }

  // Atomic Stage-A Submission
  async function handleFinalSubmit() {
    setStepError(null);
    if (selectedProducts.length === 0) {
      setStepError("Please select at least one active product vertical.");
      return;
    }

    setSubmitting(true);

    try {
      const payload: StageACompanyInput = {
        company_name: companyName.trim() || "Apex Pay Global",
        jurisdiction,
        company_size: companySize,
        company_website: companyWebsite.trim() || undefined,
        operating_licenses: selectedLicenses,
        clearing_rails: selectedRails,
        active_products: selectedProducts,
      };

      await submitStageA(payload);

      // Direct, zero-barrier redirect to live workspace / radar
      router.push("/radar");
    } catch (err: unknown) {
      setStepError(
        err instanceof Error ? err.message : "Failed to complete workspace onboarding. Please retry."
      );
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-white text-slate-900 flex flex-col font-sans selection:bg-[#2A4BFF]/10 selection:text-[#2A4BFF]">
      {/* Top Navigation Header */}
      <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200/80 px-6 sm:px-12 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StemMark compact />
          <div className="flex items-center gap-2.5">
            <span className="font-bold text-slate-900 tracking-tight text-base">
              Stem Cogent
            </span>
            <span className="text-slate-300 font-light select-none">|</span>
            <span className="text-xs sm:text-sm font-medium text-slate-500">
              Create workspace
            </span>
          </div>
        </div>

        <div className="flex items-center gap-6 text-xs sm:text-sm font-medium text-slate-500">
          <button
            type="button"
            onClick={handleRestart}
            className="inline-flex items-center gap-1.5 hover:text-slate-900 transition-colors cursor-pointer"
            title="Reset onboarding form"
          >
            <svg
              className="w-3.5 h-3.5 stroke-current"
              viewBox="0 0 24 24"
              fill="none"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
            </svg>
            <span>Restart</span>
          </button>

          <button
            type="button"
            onClick={handleLeave}
            className="inline-flex items-center gap-1.5 hover:text-slate-900 transition-colors cursor-pointer"
            title="Leave onboarding"
          >
            <svg
              className="w-3.5 h-3.5 stroke-current"
              viewBox="0 0 24 24"
              fill="none"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
            <span>Leave</span>
          </button>
        </div>
      </header>

      {/* Main Container - 1440px Canvas */}
      <div className="flex-1 w-full max-w-7xl mx-auto px-6 sm:px-12 py-8 sm:py-10 pb-24">
        {/* Mobile Horizontal Stepper */}
        <div className="lg:hidden mb-8 pb-4 border-b border-slate-200">
          <div className="flex items-center justify-between">
            {ONBOARDING_STEPS.map((s) => {
              const isActive = s.number === activeStep;
              const isCompleted = s.number < activeStep;
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setActiveStep(s.number)}
                  className="flex flex-col items-center gap-1.5"
                >
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                      isActive
                        ? "bg-slate-900 text-white"
                        : isCompleted
                        ? "bg-slate-800 text-white"
                        : "border border-slate-300 text-slate-400 bg-white"
                    }`}
                  >
                    {isCompleted ? "✓" : s.number}
                  </div>
                  <span
                    className={`text-[11px] font-medium hidden sm:inline ${
                      isActive ? "text-slate-900 font-bold" : "text-slate-400"
                    }`}
                  >
                    {s.title}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Desktop Split View: 25% Stepper / 75% Canvas */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-start">
          {/* Left Stepper Navigation (25% / 3 cols) */}
          <aside className="hidden lg:block lg:col-span-3 pr-4">
            <nav className="relative flex flex-col space-y-8" aria-label="Onboarding Progress">
              {ONBOARDING_STEPS.map((step, idx) => {
                const isActive = step.number === activeStep;
                const isCompleted = step.number < activeStep;
                const hasNext = idx < ONBOARDING_STEPS.length - 1;

                return (
                  <div key={step.id} className="relative flex items-start gap-3.5 group">
                    {/* Vertical Connector Line */}
                    {hasNext && (
                      <div
                        className={`absolute left-3.5 top-7 w-[1px] h-10 -ml-px transition-colors ${
                          step.number < activeStep ? "bg-slate-800" : "bg-slate-200"
                        }`}
                      />
                    )}

                    {/* Step Number Circle */}
                    <button
                      type="button"
                      onClick={() => setActiveStep(step.number)}
                      className={`relative z-10 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-all cursor-pointer ${
                        isActive
                          ? "bg-slate-900 text-white ring-4 ring-slate-100"
                          : isCompleted
                          ? "bg-slate-800 text-white"
                          : "border border-slate-300 text-slate-400 bg-white group-hover:border-slate-400"
                      }`}
                    >
                      {isCompleted ? (
                        <svg
                          className="w-3.5 h-3.5 stroke-current"
                          viewBox="0 0 24 24"
                          fill="none"
                          strokeWidth="2.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      ) : (
                        step.number
                      )}
                    </button>

                    {/* Step Text */}
                    <button
                      type="button"
                      onClick={() => setActiveStep(step.number)}
                      className="text-left pt-0.5 cursor-pointer"
                    >
                      <div
                        className={`text-sm tracking-tight transition-colors ${
                          isActive
                            ? "font-bold text-slate-900"
                            : isCompleted
                            ? "font-semibold text-slate-700"
                            : "font-medium text-slate-400 group-hover:text-slate-600"
                        }`}
                      >
                        {step.title}
                      </div>
                      <div
                        className={`text-xs mt-0.5 leading-snug transition-colors ${
                          isActive
                            ? "text-slate-500"
                            : "text-slate-400"
                        }`}
                      >
                        {step.subtitle}
                      </div>
                    </button>
                  </div>
                );
              })}
            </nav>
          </aside>

          {/* Right Active Flow Canvas (75% / 9 cols) */}
          <main className="lg:col-span-9 lg:pl-4 max-w-3xl">
            {/* Step Top Brand Glyph */}
            <div className="mb-6">
              <StemMark compact />
            </div>

            {/* Error Notification Banner */}
            {stepError && (
              <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200/80 text-xs text-red-700 font-medium flex items-center justify-between animate-in fade-in duration-200">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-red-600 text-sm">✕</span>
                  <span>{stepError}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setStepError(null)}
                  className="text-red-400 hover:text-red-700 cursor-pointer font-bold px-1"
                >
                  ✕
                </button>
              </div>
            )}

            {/* FLOW 1: Company Context */}
            {activeStep === 1 && (
              <div className="space-y-8 animate-in fade-in duration-150">
                <div className="space-y-1.5">
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                    Company Details
                  </h1>
                  <p className="text-sm text-slate-500">
                    This information defines your workspace and can be updated later.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
                  {/* Company Name */}
                  <div className="space-y-2 sm:col-span-2">
                    <label
                      htmlFor="companyName"
                      className="block text-xs font-semibold text-slate-700"
                    >
                      Company / Legal Entity Name<span className="text-red-500">*</span>
                    </label>
                    <input
                      id="companyName"
                      type="text"
                      required
                      placeholder="e.g. Apex Pay Global"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#2A4BFF] focus:outline-none focus:ring-1 focus:ring-[#2A4BFF] transition-shadow shadow-xs"
                    />
                  </div>

                  {/* Company Size */}
                  <div className="space-y-2">
                    <label
                      htmlFor="companySize"
                      className="block text-xs font-semibold text-slate-700"
                    >
                      Company Size<span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <select
                        id="companySize"
                        value={companySize}
                        onChange={(e) => setCompanySize(e.target.value)}
                        className="w-full appearance-none rounded-lg border border-slate-200 bg-white px-4 py-3 pr-10 text-sm text-slate-900 focus:border-[#2A4BFF] focus:outline-none focus:ring-1 focus:ring-[#2A4BFF] transition-shadow shadow-xs"
                      >
                        <option value="1-10">1-10</option>
                        <option value="11-50">11-50</option>
                        <option value="51-200">51-200</option>
                        <option value="201-500">201-500</option>
                        <option value="500+">500+</option>
                      </select>
                      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3.5 text-slate-400">
                        <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                          <path
                            fillRule="evenodd"
                            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                    </div>
                  </div>

                  {/* Primary Operating Jurisdiction */}
                  <div className="space-y-2">
                    <label
                      htmlFor="jurisdiction"
                      className="block text-xs font-semibold text-slate-700"
                    >
                      Primary Operating Jurisdiction<span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <select
                        id="jurisdiction"
                        value={jurisdiction}
                        onChange={(e) => setJurisdiction(e.target.value)}
                        className="w-full appearance-none rounded-lg border border-slate-200 bg-white px-4 py-3 pr-10 text-sm text-slate-900 focus:border-[#2A4BFF] focus:outline-none focus:ring-1 focus:ring-[#2A4BFF] transition-shadow shadow-xs"
                      >
                        <option value="Nigeria">Nigeria</option>
                        <option value="Ghana">Ghana</option>
                        <option value="Kenya">Kenya</option>
                        <option value="Pan-African">Pan-African</option>
                      </select>
                      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3.5 text-slate-400">
                        <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                          <path
                            fillRule="evenodd"
                            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                    </div>
                  </div>

                  {/* Company Website */}
                  <div className="space-y-2 sm:col-span-2">
                    <label
                      htmlFor="companyWebsite"
                      className="block text-xs font-semibold text-slate-700"
                    >
                      Company Website <span className="text-slate-400 font-normal">(Optional)</span>
                    </label>
                    <input
                      id="companyWebsite"
                      type="text"
                      placeholder="e.g. apexpay.io"
                      value={companyWebsite}
                      onChange={(e) => setCompanyWebsite(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#2A4BFF] focus:outline-none focus:ring-1 focus:ring-[#2A4BFF] transition-shadow shadow-xs"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* FLOW 2: Operating Licenses & Authorizations */}
            {activeStep === 2 && (
              <div className="space-y-8 animate-in fade-in duration-150">
                <div className="space-y-1.5">
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                    Operating Licenses & Authorizations
                  </h1>
                  <p className="text-sm text-slate-500">
                    Select all active regulatory charters, authorizations, or partner licenses held.
                  </p>
                </div>

                <div className="space-y-4 pt-2">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    {STANDARD_LICENSES.map((lic) => {
                      const isSelected = selectedLicenses.includes(lic.id);
                      return (
                        <button
                          key={lic.id}
                          type="button"
                          onClick={() => toggleLicense(lic.id)}
                          className={`flex items-start gap-3 p-4 rounded-xl border text-left transition-all cursor-pointer ${
                            isSelected
                              ? "border-[#2A4BFF] bg-blue-50/40 ring-1 ring-[#2A4BFF] shadow-xs"
                              : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50"
                          }`}
                        >
                          <div
                            className={`w-4 h-4 rounded mt-0.5 flex items-center justify-center shrink-0 transition-colors ${
                              isSelected
                                ? "bg-[#2A4BFF] text-white"
                                : "border border-slate-300 bg-white"
                            }`}
                          >
                            {isSelected && (
                              <svg
                                className="w-3 h-3 stroke-current"
                                viewBox="0 0 12 12"
                                fill="none"
                                strokeWidth="2.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              >
                                <polyline points="2.5 6 4.5 8 9.5 3" />
                              </svg>
                            )}
                          </div>
                          <div>
                            <div className="text-sm font-bold text-slate-900">
                              {lic.title}
                            </div>
                            <div className="text-xs text-slate-500 mt-0.5 leading-snug">
                              {lic.subtitle}
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  {/* Custom Licenses List & Add Trigger */}
                  <div className="pt-2 flex flex-wrap gap-2.5 items-center">
                    {selectedLicenses
                      .filter((lic) => lic.startsWith("CUSTOM:"))
                      .map((cust) => {
                        const cleanName = cust.replace(/^CUSTOM:\s*/, "");
                        return (
                          <div
                            key={cust}
                            className="inline-flex items-center gap-2 pl-3 pr-2 py-1.5 rounded-lg border border-[#2A4BFF] bg-blue-50/50 text-xs font-semibold text-slate-900"
                          >
                            <span>{cleanName}</span>
                            <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-blue-100 text-[#2A4BFF] font-bold">
                              Custom
                            </span>
                            <button
                              type="button"
                              onClick={() => removeCustomTag(cust, "license")}
                              className="text-slate-400 hover:text-red-600 transition-colors cursor-pointer"
                              title={`Remove custom license ${cleanName}`}
                            >
                              ✕
                            </button>
                          </div>
                        );
                      })}

                    {!isAddingLicense ? (
                      <button
                        type="button"
                        onClick={() => setIsAddingLicense(true)}
                        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 border border-dashed border-slate-300 hover:border-slate-400 bg-white hover:bg-slate-50 transition-colors cursor-pointer"
                      >
                        <svg
                          className="w-3.5 h-3.5 stroke-current"
                          viewBox="0 0 24 24"
                          fill="none"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                        >
                          <line x1="12" y1="5" x2="12" y2="19" />
                          <line x1="5" y1="12" x2="19" y2="12" />
                        </svg>
                        <span>Add Custom</span>
                      </button>
                    ) : (
                      <div className="inline-flex items-center gap-1.5 p-1 rounded-lg border border-[#2A4BFF] bg-white shadow-xs">
                        <input
                          type="text"
                          autoFocus
                          placeholder="e.g. SEC Digital Asset VASP"
                          value={customLicenseInput}
                          onChange={(e) => setCustomLicenseInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              handleAddCustomLicense();
                            } else if (e.key === "Escape") {
                              setIsAddingLicense(false);
                            }
                          }}
                          className="px-2.5 py-1 text-xs text-slate-900 placeholder:text-slate-400 outline-none w-48 sm:w-56"
                        />
                        <button
                          type="button"
                          onClick={handleAddCustomLicense}
                          className="px-2.5 py-1 rounded bg-[#2A4BFF] hover:bg-[#1E3AE5] text-white text-[11px] font-bold transition-colors cursor-pointer"
                        >
                          Add
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setIsAddingLicense(false);
                            setCustomLicenseInput("");
                          }}
                          className="px-2 py-1 rounded text-slate-500 hover:text-slate-800 text-[11px] font-medium transition-colors cursor-pointer"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* FLOW 3: Active Settlement & Clearing Rails */}
            {activeStep === 3 && (
              <div className="space-y-8 animate-in fade-in duration-150">
                <div className="space-y-1.5">
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                    Active Settlement & Clearing Rails
                  </h1>
                  <p className="text-sm text-slate-500">
                    Map your partner commercial banks, clearing switches, and inward rails.
                  </p>
                </div>

                <div className="space-y-4 pt-2">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    {STANDARD_RAILS.map((rail) => {
                      const isSelected = selectedRails.includes(rail.id);
                      return (
                        <button
                          key={rail.id}
                          type="button"
                          onClick={() => toggleRail(rail.id)}
                          className={`flex items-start gap-3 p-4 rounded-xl border text-left transition-all cursor-pointer ${
                            isSelected
                              ? "border-[#2A4BFF] bg-blue-50/40 ring-1 ring-[#2A4BFF] shadow-xs"
                              : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50"
                          }`}
                        >
                          <div
                            className={`w-4 h-4 rounded mt-0.5 flex items-center justify-center shrink-0 transition-colors ${
                              isSelected
                                ? "bg-[#2A4BFF] text-white"
                                : "border border-slate-300 bg-white"
                            }`}
                          >
                            {isSelected && (
                              <svg
                                className="w-3 h-3 stroke-current"
                                viewBox="0 0 12 12"
                                fill="none"
                                strokeWidth="2.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              >
                                <polyline points="2.5 6 4.5 8 9.5 3" />
                              </svg>
                            )}
                          </div>
                          <div>
                            <div className="text-sm font-bold text-slate-900">
                              {rail.title}
                            </div>
                            <div className="text-xs text-slate-500 mt-0.5 leading-snug">
                              {rail.subtitle}
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  {/* Custom Rails List & Add Trigger */}
                  <div className="pt-2 flex flex-wrap gap-2.5 items-center">
                    {selectedRails
                      .filter((rail) => rail.startsWith("CUSTOM:"))
                      .map((cust) => {
                        const cleanName = cust.replace(/^CUSTOM:\s*/, "");
                        return (
                          <div
                            key={cust}
                            className="inline-flex items-center gap-2 pl-3 pr-2 py-1.5 rounded-lg border border-[#2A4BFF] bg-blue-50/50 text-xs font-semibold text-slate-900"
                          >
                            <span>{cleanName}</span>
                            <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-blue-100 text-[#2A4BFF] font-bold">
                              Custom
                            </span>
                            <button
                              type="button"
                              onClick={() => removeCustomTag(cust, "rail")}
                              className="text-slate-400 hover:text-red-600 transition-colors cursor-pointer"
                              title={`Remove custom rail ${cleanName}`}
                            >
                              ✕
                            </button>
                          </div>
                        );
                      })}

                    {!isAddingRail ? (
                      <button
                        type="button"
                        onClick={() => setIsAddingRail(true)}
                        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 border border-dashed border-slate-300 hover:border-slate-400 bg-white hover:bg-slate-50 transition-colors cursor-pointer"
                      >
                        <svg
                          className="w-3.5 h-3.5 stroke-current"
                          viewBox="0 0 24 24"
                          fill="none"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                        >
                          <line x1="12" y1="5" x2="12" y2="19" />
                          <line x1="5" y1="12" x2="19" y2="12" />
                        </svg>
                        <span>Add Custom</span>
                      </button>
                    ) : (
                      <div className="inline-flex items-center gap-1.5 p-1 rounded-lg border border-[#2A4BFF] bg-white shadow-xs">
                        <input
                          type="text"
                          autoFocus
                          placeholder="e.g. Kora RMB Rail"
                          value={customRailInput}
                          onChange={(e) => setCustomRailInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              handleAddCustomRail();
                            } else if (e.key === "Escape") {
                              setIsAddingRail(false);
                            }
                          }}
                          className="px-2.5 py-1 text-xs text-slate-900 placeholder:text-slate-400 outline-none w-48 sm:w-56"
                        />
                        <button
                          type="button"
                          onClick={handleAddCustomRail}
                          className="px-2.5 py-1 rounded bg-[#2A4BFF] hover:bg-[#1E3AE5] text-white text-[11px] font-bold transition-colors cursor-pointer"
                        >
                          Add
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setIsAddingRail(false);
                            setCustomRailInput("");
                          }}
                          className="px-2 py-1 rounded text-slate-500 hover:text-slate-800 text-[11px] font-medium transition-colors cursor-pointer"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* FLOW 4: Active Product Verticals & Commercial Corridors */}
            {activeStep === 4 && (
              <div className="space-y-8 animate-in fade-in duration-150">
                <div className="space-y-1.5">
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                    Active Product Verticals
                  </h1>
                  <p className="text-sm text-slate-500">
                    Select the core revenue modules your fintech actively issues or operates.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
                  {STANDARD_PRODUCTS.map((prod) => {
                    const isSelected = selectedProducts.includes(prod.id);
                    return (
                      <button
                        key={prod.id}
                        type="button"
                        onClick={() => toggleProduct(prod.id)}
                        className={`flex items-start gap-3 p-4 rounded-xl border text-left transition-all cursor-pointer ${
                          isSelected
                            ? "border-[#2A4BFF] bg-blue-50/40 ring-1 ring-[#2A4BFF] shadow-xs"
                            : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50"
                        }`}
                      >
                        <div
                          className={`w-4 h-4 rounded mt-0.5 flex items-center justify-center shrink-0 transition-colors ${
                            isSelected
                              ? "bg-[#2A4BFF] text-white"
                              : "border border-slate-300 bg-white"
                          }`}
                        >
                          {isSelected && (
                            <svg
                              className="w-3 h-3 stroke-current"
                              viewBox="0 0 12 12"
                              fill="none"
                              strokeWidth="2.5"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <polyline points="2.5 6 4.5 8 9.5 3" />
                            </svg>
                          )}
                        </div>
                        <div>
                          <div className="text-sm font-bold text-slate-900">
                            {prod.title}
                          </div>
                          <div className="text-xs text-slate-500 mt-0.5 leading-snug">
                            {prod.subtitle}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Bottom Actions Footer - Sticky Docked */}
            <div className="sticky bottom-0 z-20 bg-white/95 backdrop-blur-md border-t border-slate-200/80 -mx-4 sm:-mx-6 px-4 sm:px-6 py-4 mt-8 flex items-center justify-between shadow-xs">
              {activeStep > 1 ? (
                <button
                  type="button"
                  onClick={handleBack}
                  disabled={submitting}
                  className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-sm font-medium text-slate-700 transition-colors cursor-pointer"
                >
                  <svg
                    className="w-4 h-4 stroke-current"
                    viewBox="0 0 24 24"
                    fill="none"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="15 18 9 12 15 6" />
                  </svg>
                  <span>Back</span>
                </button>
              ) : (
                <div />
              )}

              {activeStep < 4 ? (
                <button
                  type="button"
                  onClick={handleNext}
                  className="inline-flex items-center gap-1.5 px-6 py-2.5 rounded-lg bg-[#2A4BFF] hover:bg-[#1E3AE5] text-white text-sm font-medium transition-all shadow-sm cursor-pointer"
                >
                  <span>Continue</span>
                  <svg
                    className="w-4 h-4 stroke-current"
                    viewBox="0 0 24 24"
                    fill="none"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleFinalSubmit}
                  disabled={submitting}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#2A4BFF] hover:bg-[#1E3AE5] disabled:opacity-60 text-white text-sm font-medium transition-all shadow-sm cursor-pointer"
                >
                  {submitting ? (
                    <>
                      <svg
                        className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8v8H4z"
                        />
                      </svg>
                      <span>Launching Workspace…</span>
                    </>
                  ) : (
                    <>
                      <span>Complete Setup & Launch Workspace</span>
                      <span className="text-base leading-none">➔</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
