"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiRequest } from "@/lib/api";

type Citation = { source_signal_id: string; source_name: string; source_url?: string };
type Turn = {
  id: string;
  query: string;
  answer_text: string;
  citations: Citation[];
  confidence_indicator: string;
  intent?: string;
};
type Response = {
  session_id: string;
  answer_text: string;
  citations: Citation[];
  confidence_indicator: string;
  follow_up_suggestions: string[];
  intent?: string;
  working_findings?: string[];
  unresolved_questions?: string[];
};

export function CILPanel({
  anchorId,
  anchorType = "DECISION_BRIEF",
  hasRelationships = false,
  initialPrompt = "",
  suggestedInquiries,
}: {
  anchorId: string;
  anchorType?: "DECISION_BRIEF" | "SIGNAL" | "ENTITY" | "COMPANY_LENS";
  hasRelationships?: boolean;
  initialPrompt?: string;
  suggestedInquiries?: string[];
}) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [workingFindings, setWorkingFindings] = useState<string[]>([]);
  const [unresolvedQuestions, setUnresolvedQuestions] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState(initialPrompt);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (initialPrompt) {
      setQuery(initialPrompt);
    }
  }, [initialPrompt]);

  const defaultSuggested =
    suggestedInquiries && suggestedInquiries.length > 0
      ? suggestedInquiries
      : anchorType === "ENTITY"
      ? [
          "What changed recently?",
          "Why does this matter to our company?",
          ...(hasRelationships ? ["Which relationships matter most?"] : []),
          "What evidence supports this?",
        ]
      : [
          "What happened?",
          "Why does this matter to us as CFO?",
          "What evidence supports this?",
          "What decision is required?",
        ];

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const currentQuery = query.trim();
    if (currentQuery.length < 3) return;

    setSaving(true);
    setMessage("");
    try {
      const payload: {
        query: string;
        anchor_type: string;
        anchor_id: string;
        session_id?: string;
      } = {
        query: currentQuery,
        anchor_type: anchorType,
        anchor_id: anchorId,
      };
      if (sessionId) {
        payload.session_id = sessionId;
      }

      const res = await apiRequest<Response>("/api/v1/cil/query", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setSessionId(res.session_id);
      setTurns((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${prev.length}`,
          query: currentQuery,
          answer_text: res.answer_text,
          citations: res.citations || [],
          confidence_indicator: res.confidence_indicator,
          intent: res.intent,
        },
      ]);
      setWorkingFindings(res.working_findings || []);
      setUnresolvedQuestions(res.unresolved_questions || []);
      setSuggestions(res.follow_up_suggestions || []);
      setQuery("");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Cogent could not investigate this item right now."
      );
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    if (!mobileOpen) return;
    function close(event: KeyboardEvent) {
      if (event.key === "Escape") setMobileOpen(false);
    }
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [mobileOpen]);

  const activeSuggestions = suggestions.length > 0 ? suggestions : defaultSuggested;

  return (
    <>
      <button
        className="cil-mobile-trigger primary-button"
        onClick={() => setMobileOpen(true)}
        type="button"
      >
        Investigate with Cogent
      </button>
      <aside
        aria-label="Cogent investigation"
        className={mobileOpen ? "cil-panel mobile-open" : "cil-panel"}
      >
        <button
          aria-label="Close Cogent investigation"
          className="cil-mobile-close"
          onClick={() => setMobileOpen(false)}
          type="button"
        >
          ×
        </button>
        <p className="eyebrow">Investigate with Cogent</p>
        <h2>Grounded follow-up</h2>
        <p className="cil-scope">Answers stay anchored to this item and cite the evidence used.</p>

        {activeSuggestions.length > 0 && (
          <div className="cil-suggestions">
            {activeSuggestions.map((item) => (
              <button key={item} onClick={() => setQuery(item)} type="button">
                {item}
              </button>
            ))}
          </div>
        )}

        <form onSubmit={submit}>
          <label>
            <span>Question about this evidence</span>
            <textarea
              name="query"
              minLength={3}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ask Cogent (e.g. How does this affect us as CFO?)..."
              required
              value={query}
            />
          </label>
          <button
            className="primary-button"
            disabled={saving || query.trim().length < 3}
            type="submit"
          >
            {saving ? "Reviewing evidence…" : "Ask Cogent"}
          </button>
        </form>

        {message && (
          <p className="form-message" role="alert">
            {message}
          </p>
        )}

        {workingFindings.length > 0 && (
          <div className="mt-4 pt-3 border-t border-[var(--border-subtle)]">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-2">
              Working Findings
            </h3>
            <ul className="text-xs space-y-1 text-[var(--text-secondary)]">
              {workingFindings.map((finding, idx) => (
                <li key={idx} className="flex gap-1.5 items-start">
                  <span className="text-[var(--accent)]">•</span>
                  <span>{finding}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {unresolvedQuestions.length > 0 && (
          <div className="mt-3 pt-2 border-t border-[var(--border-subtle)]">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-2">
              Unresolved Questions
            </h3>
            <div className="cil-suggestions">
              {unresolvedQuestions.map((q, idx) => (
                <button key={idx} onClick={() => setQuery(q)} type="button">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.length > 0 && (
          <div className="space-y-4 mt-4">
            {turns.map((turn, i) => (
              <section key={turn.id} className="cil-answer">
                <div className="mb-2 text-xs font-semibold text-[var(--text-muted)]">
                  Turn {i + 1}: &ldquo;{turn.query}&rdquo;
                </div>
                <div className="flex gap-2 items-center mb-2">
                  <span className="verified-chip">{turn.confidence_indicator} confidence</span>
                  {turn.intent && <span className="verified-chip">{turn.intent}</span>}
                </div>
                <p>{turn.answer_text}</p>
                {turn.citations.length > 0 && (
                  <>
                    <h3>Verified evidence</h3>
                    <ul>
                      {turn.citations.map((citation, cIdx) => (
                        <li key={`${citation.source_signal_id}-${cIdx}`}>
                          {citation.source_url ? (
                            <a href={citation.source_url} rel="noreferrer" target="_blank">
                              {citation.source_name}
                            </a>
                          ) : (
                            citation.source_name
                          )}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </section>
            ))}
          </div>
        )}
      </aside>
    </>
  );
}
