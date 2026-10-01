import React from "react";

export function AuthHeroShowcase() {
  return (
    <div className="w-full h-full flex flex-col justify-between max-w-xl mx-auto py-2">
      {/* Top Hero Header */}
      <div className="space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 backdrop-blur-sm border border-white/20 text-xs font-mono font-medium tracking-wide text-white">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          Live Telemetry Mesh
        </div>
        <h2 className="text-3xl lg:text-4xl xl:text-5xl font-black text-white tracking-tight leading-[1.15]">
          Real-Time Decision Intelligence for African Fintechs
        </h2>
        <p className="text-sm lg:text-base text-blue-100 font-medium leading-relaxed max-w-lg">
          Insights that drive decisions. Continuous horizon monitoring, switch telemetry & regulatory intelligence for modern fintech leadership.
        </p>
      </div>

      {/* Center Embedded Product Preview Mockup: High-density Stem Cogent Command Canvas */}
      <div className="my-8 relative">
        {/* Glow ambient background effect */}
        <div className="absolute -inset-1 bg-gradient-to-r from-blue-400/20 to-indigo-300/20 rounded-3xl blur-xl opacity-75" />

        <div className="relative bg-white rounded-2xl shadow-2xl border border-white/30 p-5 lg:p-6 text-[#0B0F1A] overflow-hidden">
          {/* Mockup Canvas Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center gap-2.5">
              <div className="w-3 h-3 rounded-full bg-[#2A4BFF] flex items-center justify-center">
                <span className="w-1.5 h-1.5 rounded-full bg-white" />
              </div>
              <span className="text-xs font-bold tracking-tight text-[#0B0F1A]">
                Command Canvas
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">
                Lagos Mesh
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-600 font-semibold bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Synced
            </div>
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 gap-3 py-3.5 border-b border-slate-100">
            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] uppercase tracking-wider font-mono text-slate-500 block">
                Dispute Resolution SLA
              </span>
              <span className="text-base font-black text-[#0B0F1A] font-mono mt-0.5 block">
                12.4 hrs
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[10px] uppercase tracking-wider font-mono text-slate-500 block">
                Switch Volume (24h)
              </span>
              <span className="text-base font-black text-[#2A4BFF] font-mono mt-0.5 block">
                ₦8.5 Trillion
              </span>
            </div>
          </div>

          {/* Core Critical Incident & Gap Callouts */}
          <div className="pt-3.5 space-y-2.5">
            <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-slate-400 block">
              Priority Telemetry & Regulatory Actions
            </span>

            {/* 1. Providus Latency Degraded Callout */}
            <div className="p-3 rounded-xl bg-amber-50/90 border border-amber-200 flex items-start justify-between gap-3">
              <div className="flex items-start gap-2.5">
                <span className="w-2 h-2 rounded-full bg-amber-500 mt-1 flex-shrink-0" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-900">
                      Providus Latency
                    </span>
                    <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-amber-200/60 text-amber-900">
                      Degraded (18.4s)
                    </span>
                  </div>
                  <p className="text-[11px] text-amber-800/90 mt-0.5">
                    Settlement turnaround +14.2s above rolling baseline threshold.
                  </p>
                </div>
              </div>
            </div>

            {/* 2. Active Gap Callout */}
            <div className="p-3 rounded-xl bg-rose-50/90 border border-rose-200 flex items-start justify-between gap-3">
              <div className="flex items-start gap-2.5">
                <span className="w-2 h-2 rounded-full bg-rose-500 mt-1 flex-shrink-0" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-900">
                      Active Gap
                    </span>
                    <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-rose-200/60 text-rose-900">
                      2-Hour NIP Dispute Window
                    </span>
                  </div>
                  <p className="text-[11px] text-rose-800/90 mt-0.5">
                    CBN Circular SLA exposure on inter-switch claims.
                  </p>
                </div>
              </div>
            </div>

            {/* 3. Action Item Callout */}
            <div className="p-3 rounded-xl bg-blue-50/90 border border-blue-200 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span className="w-2 h-2 rounded-full bg-[#2A4BFF] flex-shrink-0" />
                <div>
                  <span className="text-xs font-bold text-slate-900 block">
                    Action Item
                  </span>
                  <span className="text-[11px] text-[#2A4BFF] font-semibold">
                    Re-route virtual accounts
                  </span>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-lg bg-[#2A4BFF] text-white text-[11px] font-bold shadow-xs">
                Auto-Mitigate
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Badges */}
      <div className="pt-2 border-t border-white/20">
        <div className="text-[11px] font-mono uppercase tracking-widest text-blue-200/80 mb-2">
          Monitored Corridors
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {["NIBSS", "Providus", "Wema", "SEC"].map((badge) => (
            <span
              key={badge}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 hover:bg-white/15 backdrop-blur-sm border border-white/20 text-xs font-mono font-semibold text-white transition-colors"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-white/70" />
              {badge}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
