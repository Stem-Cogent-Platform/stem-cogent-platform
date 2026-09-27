"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { StemMark } from "@/components/stem-mark";
import { submitStageA } from "@/lib/api";
import { DynamicTagPicker } from "@/components/ui/DynamicTagPicker";

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
  { id: "Paystack", label: "Paystack Core", desc: "Merchant & Payment Gateway" },
  { id: "Flutterwave", label: "Flutterwave Direct", desc: "Pan-African Multi-Currency" },
];

const STANDARD_PRODUCTS = [
  { id: "Virtual Accounts", label: "Virtual Accounts & Inflows", desc: "Dynamic NUBAN assignment" },
  { id: "Card Issuance", label: "Card Issuance (Verve/Visa/MC)", desc: "Physical & Virtual tokenized cards" },
  { id: "POS Acquiring", label: "POS Acquiring & Terminals", desc: "Agent banking & merchant terminals" },
  { id: "Cross-Border Trade", label: "Cross-Border FX & Remittance", desc: "Inbound & outbound FX liquidity" },
  { id: "P2P", label: "P2P & Consumer Wallets", desc: "Stored value & wallet ledgers" },
];

export default function StageAOnboardingPage() {
  const router = useRouter();

  const [companyName, setCompanyName] = useState("");
  const [selectedLicenses, setSelectedLicenses] = useState<string[]>(["PSSP"]);
  const [selectedRails, setSelectedRails] = useState<string[]>(["NIBSS", "Providus"]);
  const [selectedProducts, setSelectedProducts] = useState<string[]>(["Virtual Accounts"]);
  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!companyName.trim()) {
      setError("Please specify your company or organization name.");
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const result = await submitStageA({
        company_name: companyName.trim(),
        operating_licenses: selectedLicenses,
        active_products: selectedProducts,
        clearing_rails: selectedRails,
        primary_country: "NG",
      });

      if (!result.bootstrap_dispatched) {
        throw new Error(
          "Your footprint was saved, but intelligence preparation could not be queued. Please retry."
        );
      }
      setBootstrapping(true);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to save operational profile."
      );
      setLoading(false);
      setBootstrapping(false);
    }
  }

  if (bootstrapping) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center px-4 py-12 font-sans">
        <div className="w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-2xl p-8 sm:p-10 shadow-2xl space-y-8">
          <div className="flex items-center justify-between border-b border-slate-800 pb-6">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-400 animate-pulse">
                <StemMark compact />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-white">
                  Synthesizing Footprint Intelligence
                </h1>
                <p className="text-xs text-slate-400">
                  Bootstrapping real-time decision radar for <strong className="text-white">{companyName}</strong>
                </p>
              </div>
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse">
              Pipeline Active
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-1">
              <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                Indexed Regulatory Directives
              </div>
              <div className="text-2xl font-bold font-mono text-emerald-400">4,131+</div>
              <p className="text-[10px] text-slate-400">
                CBN, SEC & NDPC circular cross-referenced
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-1">
              <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                Selected Clearing Rails
              </div>
              <div className="text-2xl font-bold font-mono text-blue-400">
                {selectedRails.length}
              </div>
              <p className="text-[10px] text-slate-400">
                Live NIP, switch & bank telemetry nodes
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-1">
              <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                Jurisdiction Footprint
              </div>
              <div className="text-2xl font-bold font-mono text-purple-400">NG / West Africa</div>
              <p className="text-[10px] text-slate-400">
                Sovereign fintech regulatory sandbox
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-blue-950/40 border border-blue-800/40 text-xs text-blue-200/90 leading-relaxed flex items-start gap-3">
            <span className="text-blue-400 text-base mt-0.5">ℹ</span>
            <div>
              <p className="font-semibold text-blue-100">
                Operational footprint saved successfully.
              </p>
              <p className="mt-0.5">
                Our background synthesis pipeline is currently linking your specific licenses and settlement banks to active threat gazettes. Configure your executive lens in Stage B to define role-specific alerting.
              </p>
            </div>
          </div>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-4">
            <span className="text-xs text-slate-500 font-mono">
              Stage 1 of 2 Complete • Auto-proceeding to Stage B
            </span>
            <button
              type="button"
              onClick={() => router.push("/onboarding/stage-b")}
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold shadow-lg shadow-blue-600/30 transition-all flex items-center justify-center gap-2"
            >
              <span>Continue to Stage B: Personal Executive Lens</span>
              <span>➔</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50/60 text-slate-900 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* Top Enterprise Navigation Header */}
      <header className="sticky top-0 z-30 bg-white/95 backdrop-blur border-b border-slate-200 px-6 sm:px-10 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StemMark compact />
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-900 tracking-tight text-base">
              Stem Cogent
            </span>
            <span className="hidden sm:inline-block text-[11px] font-mono text-slate-400">
              | Enterprise Footprint Synthesizer
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="px-2.5 py-1 text-xs font-bold rounded-md bg-slate-900 text-white">
            Stage A of B
          </span>
          <span className="text-xs font-semibold text-slate-600">
            Operational Footprint
          </span>
        </div>
      </header>

      {/* Main Split-Canvas Layout */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-10">
        <form onSubmit={handleSubmit} className="space-y-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left Context Column: 35% Width (approx 4 of 12 cols on desktop) */}
            <aside className="lg:col-span-4 space-y-6 lg:sticky lg:top-20">
              <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-7 shadow-xs space-y-5">
                <div className="space-y-2">
                  <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-[11px] font-bold uppercase tracking-wider border border-blue-200/60">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
                    Jurisdiction Context
                  </div>
                  <h1 className="text-2xl font-black tracking-tight text-slate-900">
                    Declare Your Operational Footprint
                  </h1>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Stem Cogent filters out market noise by cross-referencing{" "}
                    <strong className="text-slate-900">4,131+ RDS regulatory circulars</strong> and live switch incident feeds against your active licenses, clearing rails, and product verticals.
                  </p>
                </div>

                {/* Real-time Footprint Telemetry Badges */}
                <div className="pt-4 border-t border-slate-100 space-y-3">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    Real-time Footprint Metrics
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/70">
                      <span className="block text-lg font-black text-slate-900">
                        {selectedLicenses.length}
                      </span>
                      <span className="text-[10px] font-medium text-slate-500">Licenses</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/70">
                      <span className="block text-lg font-black text-slate-900">
                        {selectedRails.length}
                      </span>
                      <span className="text-[10px] font-medium text-slate-500">Rails</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/70">
                      <span className="block text-lg font-black text-slate-900">
                        {selectedProducts.length}
                      </span>
                      <span className="text-[10px] font-medium text-slate-500">Products</span>
                    </div>
                  </div>
                </div>

                {/* Strategic Context Note */}
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px] text-slate-600 leading-normal space-y-1">
                  <div className="font-bold text-slate-800 flex items-center gap-1.5">
                    <span>🛡️ Sovereign Nigerian Coverage</span>
                  </div>
                  <p>
                    Adding custom licenses (e.g. SEC Digital Asset VASP, Finance Company) or specialized settlement rails (e.g. Kora, VFD) enables targeted regulatory horizon scanning immediately.
                  </p>
                </div>
              </div>
            </aside>

            {/* Right Canvas Column: 65% Width (approx 8 of 12 cols on desktop) */}
            <div className="lg:col-span-8 space-y-6">
              <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xs space-y-8">
                {error && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 font-medium flex items-center gap-2">
                    <span className="text-red-500 font-bold">✕</span>
                    <span>{error}</span>
                  </div>
                )}

                {/* Section 1: Legal Entity Name */}
                <div className="space-y-2">
                  <label
                    htmlFor="companyName"
                    className="block text-xs font-bold uppercase tracking-wider text-slate-800"
                  >
                    1. Company / Legal Entity Name
                  </label>
                  <input
                    id="companyName"
                    type="text"
                    required
                    placeholder="e.g. Apex Pay Global Technologies Ltd"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="block w-full rounded-xl border border-slate-300 px-4 py-3 text-sm font-medium text-slate-900 placeholder-slate-400 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/10 shadow-2xs transition"
                  />
                  <p className="text-[11px] text-slate-500">
                    The legal entity under which your payment infrastructure and regulatory filings operate.
                  </p>
                </div>

                <div className="border-t border-slate-100 pt-6">
                  {/* Section 2: Operating Licenses */}
                  <DynamicTagPicker
                    id="operating-licenses-picker"
                    label="2. Operating Licenses Held or Partnered"
                    description="Select all standard license tiers or add custom licenses"
                    standardOptions={STANDARD_LICENSES}
                    selected={selectedLicenses}
                    onChange={setSelectedLicenses}
                    customPlaceholder="e.g. SEC Digital Asset VASP, Finance Co."
                    categoryName="license"
                  />
                </div>

                <div className="border-t border-slate-100 pt-6">
                  {/* Section 3: Active Clearing Rails & Partner Banks */}
                  <DynamicTagPicker
                    id="clearing-rails-picker"
                    label="3. Active Settlement & Clearing Rails"
                    description="Live commercial corridors, switch connections, and bank nodes"
                    standardOptions={STANDARD_RAILS}
                    selected={selectedRails}
                    onChange={setSelectedRails}
                    customPlaceholder="e.g. Kora RMB Rail, VFD Microfinance, Moniepoint"
                    categoryName="rail"
                  />
                </div>

                <div className="border-t border-slate-100 pt-6">
                  {/* Section 4: Active Product Modules */}
                  <DynamicTagPicker
                    id="product-modules-picker"
                    label="4. Active Product Verticals & Commercial Corridors"
                    description="Modules that power your client revenue and transaction processing"
                    standardOptions={STANDARD_PRODUCTS}
                    selected={selectedProducts}
                    onChange={setSelectedProducts}
                    customPlaceholder="e.g. Agency Banking Super-Node, Payroll FX"
                    categoryName="product"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Persistent Bottom Action Bar */}
          <div className="sticky bottom-0 z-20 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-8 py-4 bg-white/90 backdrop-blur-md border-t border-slate-200 shadow-lg">
            <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2.5 text-xs text-slate-600">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-medium">Ready to bootstrap workspace intelligence</span>
                <span className="hidden md:inline text-slate-300">•</span>
                <span className="hidden md:inline text-slate-500">
                  {selectedLicenses.length} licenses & {selectedRails.length} rails configured
                </span>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full sm:w-auto px-7 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2 disabled:opacity-50 transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-98"
              >
                {loading ? (
                  <span>Saving Operational Footprint…</span>
                ) : (
                  <>
                    <span>Continue to Stage B: Personal Executive Lens</span>
                    <span>➔</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </main>
    </div>
  );
}
