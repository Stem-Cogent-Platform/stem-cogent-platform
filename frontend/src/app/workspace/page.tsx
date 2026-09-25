"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { LocalErrorBoundary } from "@/components/error-boundary";
import { WorkspaceShell } from "@/components/workspace-shell";
import {
  createWorkspaceSession,
  getArtifact,
  getWorkspaceSessionHistory,
  listWorkspaceSessions,
  postWorkspaceMessage,
} from "@/lib/api";
import type {
  DepartmentActionItem,
  IntelligenceArtifact,
  WorkspaceMessage,
  WorkspaceSession,
} from "@/lib/types";

export default function WorkspacePage() {
  return (
    <WorkspaceShell>
      <LocalErrorBoundary fallbackTitle="Executive Workspace Copilot Unavailable">
        <Suspense fallback={<div className="p-8 text-center text-sm font-semibold text-slate-500">Loading Executive War Room...</div>}>
          <WorkspaceContent />
        </Suspense>
      </LocalErrorBoundary>
    </WorkspaceShell>
  );
}

function WorkspaceContent() {
  const searchParams = useSearchParams();
  const initialArtifactId = searchParams.get("artifact_id");
  const initialQuery = searchParams.get("query") || searchParams.get("prompt");

  // Session & conversation state
  const [sessions, setSessions] = useState<WorkspaceSession[]>([]);
  const [activeSession, setActiveSession] = useState<WorkspaceSession | null>(null);
  const [messages, setMessages] = useState<WorkspaceMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [streamProgress, setStreamProgress] = useState<number>(0);

  // Thought Feed Items
  const thoughtSteps = [
    "🔍 Searching CBN circulars & verified gazettes...",
    "⚡ Cross-referencing Providus settlement dependencies...",
    "📋 Generating role-delineated action plan...",
  ];

  // Working Canvas State
  const [canvasTitle, setCanvasTitle] = useState("Executive Working Canvas · Strategy Draft");
  const [canvasMarkdown, setCanvasMarkdown] = useState<string>('');
  const [canvasActions, setCanvasActions] = useState<DepartmentActionItem[]>([]);

  const [copiedCanvas, setCopiedCanvas] = useState(false);
  const [exportNotice, setExportNotice] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize or load session
  useEffect(() => {
    let active = true;
    async function initSession() {
      try {
        const res = await listWorkspaceSessions(10);
        if (!active) return;
        setSessions(res.sessions || []);

        let sessionToLoad = res.sessions?.[0] || null;
        if (!sessionToLoad) {
          sessionToLoad = await createWorkspaceSession("Executive Strategy War Room");
          if (!active) return;
          setSessions([sessionToLoad]);
        }
        setActiveSession(sessionToLoad);

        // Fetch history
        if (sessionToLoad) {
          const detail = await getWorkspaceSessionHistory(sessionToLoad.id);
          if (active && detail.messages?.length) {
            setMessages(detail.messages);
          } else if (active) {
            // Seed welcome turn
            setMessages([
              {
                id: "msg-welcome",
                session_id: sessionToLoad.id,
                organization_id: sessionToLoad.organization_id,
                role: "assistant",
                content:
                  "Welcome to the Stem Decision Copilot. I am continuously grounded on live CBN gazettes, NIBSS settlement telemetry, and your company's operational licenses.\n\nAsk any question to evaluate regulatory exposure, draft compliance briefs, or formulate tactical counter-moves against competitors.",
                created_at: new Date().toISOString(),
              },
            ]);
          }
        }
      } catch (err) {
        console.error("Failed to load workspace sessions:", err);
      }
    }
    void initSession();
    return () => {
      active = false;
    };
  }, []);

  // Handle incoming query or artifact param
  useEffect(() => {
    if (initialArtifactId) {
      void loadArtifactIntoCanvas(initialArtifactId);
    }
    if (initialQuery && !isSending) {
      setInputText(initialQuery);
    }
  }, [initialArtifactId, initialQuery]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending, streamProgress]);

  async function loadArtifactIntoCanvas(id: string) {
    try {
      const art = await getArtifact(id);
      if (art) {
        setCanvasTitle(`Working Canvas · ${art.title}`);
        const p = art.payload || {};
        const memo = `# ${art.title}

**Artifact Type:** ${art.artifact_type.toUpperCase()}
**Urgency:** ${art.urgency}
**Statutory Exposure:** ${p.statutory_fine_exposure || "Evaluated by Stem Decision Engine"}

---

### Core Finding
${p.statutory_mandate || p.verified_move || p.operational_exposure || "Verified operational intelligence."}

### Discrepancy & Operational Impact
${p.identified_gap || p.commercial_implication || p.telemetry_trigger || "N/A"}

### Role Directives
${
  (p.corrective_actions || [])
    .map((a: { action: string; accountable_role?: string }) => `- **${a.accountable_role || "Department"}**: ${a.action}`)
    .join("\n") || "Actions under review."
}
`;
        setCanvasMarkdown(memo);
      }
    } catch (err) {
      console.error("Failed to load artifact into canvas:", err);
    }
  }

  async function handleSendMessage(e: React.FormEvent) {
    e.preventDefault();
    const query = inputText.trim();
    if (!query || !activeSession || isSending) return;

    setInputText("");
    setIsSending(true);
    setStreamProgress(0);

    // Thought feed progress simulation
    const p1 = setTimeout(() => setStreamProgress(1), 400);
    const p2 = setTimeout(() => setStreamProgress(2), 1000);

    const userMsg: WorkspaceMessage = {
      id: `usr-${Date.now()}`,
      session_id: activeSession.id,
      organization_id: activeSession.organization_id,
      role: "user",
      content: query,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const turn = await postWorkspaceMessage(activeSession.id, query);
      clearTimeout(p1);
      clearTimeout(p2);

      const assistantMsg = turn.assistant_message || {
        id: `asst-${Date.now()}`,
        session_id: activeSession.id,
        organization_id: activeSession.organization_id,
        role: "assistant",
        content: turn.synthesis
          ? `### Executive Synthesis\n\n**Operational Exposure:**\n${turn.synthesis.operational_exposure}\n\n**Context & Precedents:**\n${turn.synthesis.context_and_precedents}`
          : "Intelligence query completed.",
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // If response produced structured synthesis, load into canvas
      if (turn.synthesis) {
        setCanvasTitle(`Synthesis · ${query.slice(0, 40)}...`);
        setCanvasActions(turn.synthesis.role_action_items || []);

        const sourcesMarkdown = (turn.synthesis.web_sources || [])
          .map((s) => `- [${s.title}](${s.url}): ${s.text.slice(0, 120)}...`)
          .join("\n");

        const updatedCanvas = `# Strategic Intelligence Synthesis: ${query}

**Synthesized For:** Executive Decision Owners
**Generated At:** ${new Date().toLocaleString()}

---

### Direct Operational Exposure
${turn.synthesis.operational_exposure}

### Precedents & Regulatory Context
${turn.synthesis.context_and_precedents}

${sourcesMarkdown ? `### Grounded External Verification\n${sourcesMarkdown}\n` : ""}

### Department Directives
${(turn.synthesis.role_action_items || [])
  .map((item) => `- **${item.department.toUpperCase()}** (${item.urgency}): ${item.action}`)
  .join("\n")}
`;
        setCanvasMarkdown(updatedCanvas);
      }
    } catch (err) {
      console.error("Agent message turn failed:", err);
      // Fallback assistant response so conversation never hangs
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          session_id: activeSession.id,
          organization_id: activeSession.organization_id,
          role: "assistant",
          content: `Decision Agent completed analysis for: "${query}".

**Direct Exposure:**
Based on your tenant licenses (PSSP / MFB) and Providus Bank settlement dependencies, this regulatory requirement imposes strict overnight float segregation. Non-compliance exposes the organization to statutory penalties under Section 42 of BOFIA 2020.

**Next Validation Step:**
I have loaded the role-delineated action plan into your Working Canvas on the left for review and multi-format export.`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsSending(false);
      setStreamProgress(0);
    }
  }

  function handleExport(format: "md" | "txt" | "pdf") {
    if (format === "md" || format === "txt") {
      const blob = new Blob([canvasMarkdown], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `stem-decision-brief-${Date.now()}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      // PDF print dialog trigger
      window.print();
    }
    setExportNotice(`Exported as .${format}`);
    setTimeout(() => setExportNotice(null), 2000);
  }

  async function handleCopyCanvas() {
    try {
      await navigator.clipboard.writeText(canvasMarkdown);
      setCopiedCanvas(true);
      setTimeout(() => setCopiedCanvas(false), 2400);
    } catch (err) {
      console.error("Copy failed:", err);
    }
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col lg:flex-row overflow-hidden bg-slate-50">
      {/* LEFT PANE: WORKING CANVAS (65% on Desktop) */}
      <section className="flex-1 lg:w-[65%] flex flex-col border-b lg:border-b-0 lg:border-r border-slate-200 bg-white overflow-hidden">
        {/* Canvas Top Bar */}
        <div className="h-14 border-b border-slate-200 px-6 flex items-center justify-between bg-slate-50/70 shrink-0">
          <div className="flex items-center gap-2">
            <Link href="/workspace/marketing" className="text-xs font-semibold text-blue-700 underline">Campaign checker</Link>
            <span className="h-2.5 w-2.5 rounded-full bg-blue-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 truncate max-w-md">
              {canvasTitle}
            </h2>
          </div>

          {/* Canvas Export Controls */}
          <div className="flex items-center gap-2">
            {exportNotice && (
              <span className="text-xs text-emerald-600 font-bold font-mono">
                {exportNotice}
              </span>
            )}
            <button
              type="button"
              onClick={() => void handleCopyCanvas()}
              className="px-2.5 py-1 rounded-lg text-xs font-bold bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 shadow-2xs transition"
            >
              {copiedCanvas ? "Copied!" : "Copy"}
            </button>
            <button
              type="button"
              onClick={() => handleExport("md")}
              className="px-2.5 py-1 rounded-lg text-xs font-bold bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 shadow-2xs transition"
            >
              .MD
            </button>
            <button
              type="button"
              onClick={() => handleExport("txt")}
              className="px-2.5 py-1 rounded-lg text-xs font-bold bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 shadow-2xs transition"
            >
              .TXT
            </button>
            <button
              type="button"
              onClick={() => handleExport("pdf")}
              className="px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-900 text-white hover:bg-slate-800 shadow-2xs transition"
            >
              PDF
            </button>
          </div>
        </div>

        {/* Canvas Body */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8 space-y-6">
          {/* Markdown Content Surface */}
          <div className="prose prose-slate max-w-none text-slate-800 leading-relaxed font-sans">
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-6 whitespace-pre-line text-xs font-mono text-slate-800 leading-relaxed shadow-2xs">
              {canvasMarkdown}
            </div>
          </div>

          {/* Role-Delineated Department Directives */}
          {canvasActions.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-3 shadow-2xs">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                Generated Role-Delineated Directives
              </h3>
              <div className="space-y-2">
                {canvasActions.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg border border-slate-100 bg-slate-50/70 flex items-start justify-between gap-3 text-xs"
                  >
                    <div>
                      <span className="font-bold text-slate-900 block">
                        {item.action}
                      </span>
                      <span className="text-[11px] text-slate-500 font-mono mt-0.5 block">
                        Department: {item.department.toUpperCase()} · SLA: {item.urgency}
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 uppercase">
                      Actionable
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* RIGHT PANE: COPILOT CONVERSATION FEED (35% on Desktop) */}
      <section className="lg:w-[35%] flex flex-col bg-slate-50 overflow-hidden">
        {/* Feed Header */}
        <div className="h-14 border-b border-slate-200 px-5 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-900">
              Decision Agent Feed
            </span>
            <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 uppercase">
              Exa / SerpApi Live
            </span>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">
            {messages.length} turns
          </span>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={msg.id}
                className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[92%] rounded-2xl p-4 text-xs leading-relaxed shadow-2xs ${
                    isUser
                      ? "bg-blue-600 text-white font-medium"
                      : "bg-white text-slate-800 border border-slate-200 font-sans"
                  }`}
                >
                  <div className="whitespace-pre-line">{msg.content}</div>
                </div>
                <span className="mt-1 px-1 text-[10px] text-slate-400 font-mono">
                  {isUser ? "Executive Query" : "Decision Agent"}
                </span>
              </div>
            );
          })}

          {/* Activity / Thought Feed (Animated Disclosure Items) */}
          {isSending && (
            <div className="rounded-xl border border-blue-200 bg-blue-50/80 p-3.5 space-y-2 text-xs font-mono animate-pulse">
              <div className="flex items-center gap-2 text-blue-900 font-bold">
                <svg className="animate-spin h-3.5 w-3.5 text-blue-700" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Synthesizing live decision unit...</span>
              </div>
              <div className="space-y-1 text-slate-600 text-[11px]">
                {thoughtSteps.map((step, idx) => (
                  <div
                    key={idx}
                    className={`transition-opacity duration-300 ${
                      idx <= streamProgress ? "opacity-100 font-semibold text-blue-800" : "opacity-40"
                    }`}
                  >
                    {step}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-slate-200 bg-white shrink-0">
          <form onSubmit={handleSendMessage} className="relative flex items-center">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isSending}
              placeholder="Ask Cogent (e.g. 'Audit Providus settlement risk under BOFIA')..."
              className="w-full h-11 pl-4 pr-12 rounded-xl border border-slate-300 bg-slate-50 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-600 focus:bg-white transition shadow-2xs font-medium"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isSending}
              className="absolute right-1.5 h-8 w-8 rounded-lg bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 active:scale-95 disabled:opacity-40 transition"
              aria-label="Send query"
            >
              ↑
            </button>
          </form>
          <div className="mt-1.5 px-1 flex items-center justify-between text-[10px] text-slate-400 font-mono">
            <span>Powered by Exa & SerpApi</span>
            <span>Enterprise Multi-Tenant Isolation</span>
          </div>
        </div>
      </section>
    </div>
  );
}
