"use client";

import { useState } from "react";
import { updateExecutiveStance } from "@/lib/api";
import type { IntelligenceArtifact } from "@/lib/types";

interface Props {
  artifact: IntelligenceArtifact;
  onUpdate?: (updated: IntelligenceArtifact) => void;
}

type StanceType = "counter_attack" | "monitor" | "ignore";
type TabType = "attack_defense" | "licensing_charters" | "margin_pricing";

export function CompetitiveBattlecard({ artifact, onUpdate }: Props) {
  const payload = artifact.payload || {};
  const competitorName = payload.competitor_name || "Ecosystem Rival";
  const verifiedMove = payload.verified_move || "Launched zero-fee virtual account settlement and private clearing corridor.";
  const commercialImplication = payload.commercial_implication || "Erodes transaction take-rates by 35-50 bps on mid-market checkout flows.";
  const vulnerableSegments = payload.vulnerable_segments || ["Tier-2 E-commerce Merchants", "Cross-Border Payout Aggregators", "Lending Fintechs"];

  // Executive Stance
  const initialStance: StanceType =
    (payload.executive_stance?.stance as StanceType) ||
    (payload.stance as StanceType) ||
    "monitor";

  const [currentStance, setCurrentStance] = useState<StanceType>(initialStance);
  const [updatingStance, setUpdatingStance] = useState<StanceType | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("attack_defense");

  // Accordion state for trap-setting moves
  const [openAccordion, setOpenAccordion] = useState<number | null>(0);

  // Clipboard copy state
  const [copiedTrackId, setCopiedTrackId] = useState<string | null>(null);

  // Scripted objection handling & talk tracks (Klue Model)
  const talkTracks = [
    {
      id: "track-1",
      objection: "Competitor is offering 0.5% flat settlement fees vs your 1.2% rate.",
      response: `When the merchant brings up their 0.5% rate:
"Their 0.5% rate relies on a Tier-2 MFB sponsor with a 72-hour rolling settlement reserve and frequent weekend NIP debit drops. With Stem, you receive instant T+0 settlement backed by Providus & Wema dual-node redundancy, meaning 0% delayed payouts and 99.8% checkout success."`,
      landmine: "Ask them: 'What is their SLA on trapped merchant funds when their single sponsor bank experiences core maintenance on Sunday evening?'",
    },
    {
      id: "track-2",
      objection: "Competitor claims they now have a full direct CBN payment license.",
      response: `When the prospect cites their new license announcement:
"While they did secure an Approval-In-Principle (AIP) for a PSSP, AIP does not permit direct clearing on NIBSS switches without a commercial bank escrow trustee. Stem operates with fully validated enterprise trustees, keeping your merchant funds 100% ringfenced and protected under BOFIA 2020."`,
      landmine: "Ask them: 'Can they provide your legal team with an active CBN Operating Gazette certificate, or just the provisional AIP letter?'",
    },
  ];

  // Trap Setting Moves
  const trapSettingMoves = [
    {
      id: 1,
      title: "The Subsidized Float Trap",
      verifiedFact: "Competitor is absorbing sponsor bank transfer fees to artificially lower headline transaction costs.",
      marginSqueeze: "At ₦45 true interchange cost per transfer, their 0.5% fee on a ₦5,000 ticket yields a net loss of ₦20 per checkout.",
      counterMove: "Offer merchants tiered volume discounts paired with real-time automated settlement reconciliation, exposing their unsustainable unit economics.",
    },
    {
      id: 2,
      title: "The Single-Rail Dependency Vulnerability",
      verifiedFact: "100% of their dynamic virtual accounts route exclusively through a single regional microfinance bank.",
      marginSqueeze: "A 4-hour sponsor core outage creates an immediate 38% cart abandonment rate across connected merchant checkouts.",
      counterMove: "Provide prospective merchants with our live multi-bank rail uptime widget demonstrating zero downtime failover.",
    },
  ];

  async function handleSetStance(newStance: StanceType) {
    if (newStance === currentStance || updatingStance) return;
    setUpdatingStance(newStance);
    const prev = currentStance;
    setCurrentStance(newStance);

    try {
      const res = await updateExecutiveStance(artifact.id, newStance);
      if (onUpdate && res) {
        onUpdate({
          ...artifact,
          payload: {
            ...artifact.payload,
            executive_stance: res.executive_stance as any,
          },
        });
      }
    } catch (err) {
      setCurrentStance(prev);
      console.error("Failed to update executive stance:", err);
    } finally {
      setUpdatingStance(null);
    }
  }

  async function handleCopyTalkTrack(trackId: string, text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedTrackId(trackId);
      setTimeout(() => {
        setCopiedTrackId(null);
      }, 2400);
    } catch (err) {
      console.error("Clipboard copy failed:", err);
    }
  }

  return (
    <div className="group relative rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_1px_2px_rgba(0,0,0,0.05)] hover:shadow-[0_4px_12px_rgba(0,0,0,0.08)] transition-all duration-200 hover:-translate-y-0.5">
      {/* Top Bar: Competitor Identity & Executive Stance Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-purple-50 text-purple-700 border border-purple-200">
              Competitive Battlecard
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold text-slate-500 bg-slate-100 border border-slate-200">
              Commercial Intelligence
            </span>
          </div>
          <h3 className="mt-2 text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>{competitorName}</span>
            <span className="text-slate-400 font-normal">·</span>
            <span className="text-sm font-semibold text-slate-600">{artifact.title}</span>
          </h3>
        </div>

        {/* Strategy Stance Toggle Buttons */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-100 border border-slate-200">
          <span className="px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Stance:
          </span>
          <button
            type="button"
            onClick={() => void handleSetStance("counter_attack")}
            disabled={updatingStance !== null}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              currentStance === "counter_attack"
                ? "bg-red-600 text-white shadow-xs"
                : "text-slate-700 hover:text-red-700 hover:bg-white/80"
            }`}
          >
            Counter-Attack
          </button>
          <button
            type="button"
            onClick={() => void handleSetStance("monitor")}
            disabled={updatingStance !== null}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              currentStance === "monitor"
                ? "bg-slate-900 text-white shadow-xs"
                : "text-slate-700 hover:text-slate-900 hover:bg-white/80"
            }`}
          >
            Monitor
          </button>
          <button
            type="button"
            onClick={() => void handleSetStance("ignore")}
            disabled={updatingStance !== null}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              currentStance === "ignore"
                ? "bg-slate-400 text-white shadow-xs"
                : "text-slate-700 hover:text-slate-900 hover:bg-white/80"
            }`}
          >
            Ignore
          </button>
        </div>
      </div>

      {/* Verified Move & Commercial Threat Banner */}
      <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50/80 p-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Verified Market Move
            </span>
          </div>
          <p className="text-sm font-semibold text-slate-900 leading-snug">
            {verifiedMove}
          </p>
          <p className="text-xs text-slate-600">
            <span className="font-semibold text-red-600">Commercial Threat:</span> {commercialImplication}
          </p>
          <div className="pt-2 flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-semibold text-slate-500">At-Risk Segments:</span>
            {vulnerableSegments.map((seg, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-white text-slate-700 border border-slate-200 shadow-2xs"
              >
                {seg}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Dense Modular Quick-Filter Pills */}
      <div className="mt-6 flex items-center gap-2 border-b border-slate-100 pb-3">
        <button
          type="button"
          onClick={() => setActiveTab("attack_defense")}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
            activeTab === "attack_defense"
              ? "bg-blue-600 text-white shadow-xs"
              : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          }`}
        >
          Attack & Defense (Talk Tracks)
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("licensing_charters")}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
            activeTab === "licensing_charters"
              ? "bg-blue-600 text-white shadow-xs"
              : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          }`}
        >
          Licensing & Charters
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("margin_pricing")}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
            activeTab === "margin_pricing"
              ? "bg-blue-600 text-white shadow-xs"
              : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          }`}
        >
          Margin & Pricing Squeeze
        </button>
      </div>

      {/* Tab Content */}
      <div className="mt-5">
        {activeTab === "attack_defense" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Scripted Commercial Objection Handling ("Say")
              </span>
              <span className="text-[11px] text-slate-400">
                Ready to paste into WhatsApp / Slack / Email
              </span>
            </div>

            {talkTracks.map((track) => {
              const isCopied = copiedTrackId === track.id;
              return (
                <div
                  key={track.id}
                  className="rounded-xl border border-slate-200 bg-white p-4.5 shadow-2xs space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">
                        ?
                      </span>
                      <span className="text-xs font-bold text-slate-900">
                        {track.objection}
                      </span>
                    </div>

                    {/* One-Click Sales Talk Track Copier */}
                    <button
                      type="button"
                      onClick={() => void handleCopyTalkTrack(track.id, track.response)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-2xs ${
                        isCopied
                          ? "bg-emerald-600 text-white"
                          : "bg-slate-900 text-white hover:bg-slate-800 active:scale-95"
                      }`}
                    >
                      {isCopied ? (
                        <>
                          <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                          <span>Copied to Clipboard!</span>
                        </>
                      ) : (
                        <>
                          <svg className="h-3.5 w-3.5 text-slate-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                          </svg>
                          <span>Copy Talk Track</span>
                        </>
                      )}
                    </button>
                  </div>

                  <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-800 leading-relaxed font-sans border border-slate-100 whitespace-pre-line">
                    {track.response}
                  </div>

                  {track.landmine && (
                    <div className="flex items-start gap-2 text-xs text-amber-900 bg-amber-50/70 p-2.5 rounded-lg border border-amber-200/70">
                      <span className="font-bold shrink-0">💣 Landmine Question:</span>
                      <span className="italic">{track.landmine}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {activeTab === "licensing_charters" && (
          <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Regulatory Charter & Authorization Reality
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                <span className="text-[11px] font-bold text-slate-400 uppercase">License Posture</span>
                <p className="mt-1 text-sm font-semibold text-slate-800">
                  Switching & Processing License Pending (AIP Stage)
                </p>
                <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                  Competitor remains dependent on a partner sponsor bank for final settlement clearance on Central Bank of Nigeria RTGS.
                </p>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                <span className="text-[11px] font-bold text-slate-400 uppercase">Regulatory Vulnerability</span>
                <p className="mt-1 text-sm font-semibold text-red-700">
                  BoFIA 2020 Compliance Exposure
                </p>
                <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                  Holding merchant funds overnight in unsegregated clearing accounts violates CBN circular on PSSP float restrictions.
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === "margin_pricing" && (
          <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Margin Squeeze Breakdown & Pricing Counter-Plays
            </h4>
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800">Rival Subsidized Interchange Spread</span>
                <span className="text-xs font-mono font-bold text-red-600">-0.65% blended net margin</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                By charging a flat 0.5% fee while paying ₦45 + 0.3% to clearing switches, the competitor burns capital on every transaction below ₦12,000.
              </p>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs font-medium text-slate-700">
                <span>Recommended Counter:</span>
                <span className="font-bold text-blue-600">Bundle High-Volume T+0 API Access</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Trap-Setting Accordions (Animated Transitions) */}
      <div className="mt-6 pt-5 border-t border-slate-100">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
          Tactical Trap-Setting Moves
        </h4>

        <div className="space-y-2.5">
          {trapSettingMoves.map((move, idx) => {
            const isOpen = openAccordion === idx;
            return (
              <div
                key={move.id}
                className="rounded-xl border border-slate-200 bg-white overflow-hidden transition-all shadow-2xs"
              >
                <button
                  type="button"
                  onClick={() => setOpenAccordion(isOpen ? null : idx)}
                  className="w-full flex items-center justify-between p-3.5 text-left bg-slate-50/50 hover:bg-slate-50 transition"
                >
                  <span className="text-xs font-bold text-slate-900">
                    {move.title}
                  </span>
                  <span className="text-slate-400 text-sm font-bold">
                    {isOpen ? "−" : "+"}
                  </span>
                </button>

                {isOpen && (
                  <div className="p-4 space-y-3 border-t border-slate-100 bg-white text-xs leading-relaxed">
                    <div>
                      <strong className="text-slate-700 block">1. Verified Fact:</strong>
                      <span className="text-slate-600">{move.verifiedFact}</span>
                    </div>
                    <div>
                      <strong className="text-red-700 block">2. Margin Squeeze Calculation:</strong>
                      <span className="text-red-900 font-mono text-[11px] bg-red-50 p-1.5 rounded block mt-0.5 border border-red-100">
                        {move.marginSqueeze}
                      </span>
                    </div>
                    <div>
                      <strong className="text-blue-700 block">3. Commercial Counter-Move:</strong>
                      <span className="text-slate-700">{move.counterMove}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
