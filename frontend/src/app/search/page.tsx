"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useCallback, useEffect, useState } from "react";

import { CILPanel } from "@/components/cil-panel";
import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest, recordProductEvent } from "@/lib/api";
import { LoadState } from "@/lib/types";

type SearchItem = {
  id: string;
  signal_id?: string;
  title: string;
  summary?: string;
  domain?: string;
  urgency?: string;
};

type SearchResults = {
  query: string;
  is_question?: boolean;
  total_count?: number;
  briefs: SearchItem[];
  intelligence: SearchItem[];
  entities: SearchItem[];
  cogent_inquiry?: {
    prompt: string;
    suggested_angles: string[];
  };
};

function Results() {
  const router = useRouter();
  const params = useSearchParams();
  const initialQuery = params.get("q")?.trim() ?? "";

  const [inputQuery, setInputQuery] = useState(initialQuery);
  const [state, setState] = useState<LoadState<SearchResults>>({ status: "loading" });
  const [activeInvestigation, setActiveInvestigation] = useState<{
    prompt: string;
    suggested?: string[];
  } | null>(null);

  useEffect(() => {
    setInputQuery(initialQuery);
  }, [initialQuery]);

  const load = useCallback(async () => {
    if (initialQuery.length < 2) {
      setState({
        status: "ready",
        data: { query: initialQuery, briefs: [], intelligence: [], entities: [] },
      });
      return;
    }
    try {
      setState({ status: "loading" });
      const data = await apiRequest<SearchResults>(`/api/v1/search?q=${encodeURIComponent(initialQuery)}`);
      setState({ status: "ready", data });
      void recordProductEvent("SEARCH_PERFORMED", {
        metadata: { query: initialQuery, total_count: data.total_count ?? 0 },
      });

      // If user typed an explicit question, pre-configure the investigation prompt
      if (data.is_question && data.cogent_inquiry) {
        setActiveInvestigation({
          prompt: data.cogent_inquiry.prompt,
          suggested: data.cogent_inquiry.suggested_angles,
        });
      }
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Search could not be completed.",
      });
    }
  }, [initialQuery]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const handleSearchSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const clean = inputQuery.trim();
    if (clean.length >= 2) {
      router.push(`/search?q=${encodeURIComponent(clean)}`);
    }
  };

  const startCogentInvestigation = (promptText?: string) => {
    const prompt = promptText || (state.status === "ready" && state.data.cogent_inquiry?.prompt) || inputQuery || initialQuery;
    const suggested = state.status === "ready" ? state.data.cogent_inquiry?.suggested_angles : undefined;
    setActiveInvestigation({ prompt, suggested });
  };

  return (
    <div style={{ display: "grid", gap: "24px" }}>
      {/* Chrome-Style Omnibox Search Bar */}
      <form
        onSubmit={handleSearchSubmit}
        role="search"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          background: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: "14px",
          padding: "10px 18px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
        }}
      >
        <span aria-hidden="true" style={{ fontSize: "1.2rem", color: "var(--text-secondary)" }}>
          ⌕
        </span>
        <input
          aria-label="Search intelligence or ask Cogent"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          placeholder="Search intelligence or ask Cogent…"
          type="search"
          style={{
            flex: 1,
            border: "none",
            outline: "none",
            fontSize: "1.05rem",
            background: "transparent",
            color: "var(--text-primary)",
          }}
        />
        <button
          type="submit"
          className="primary-button"
          style={{
            fontSize: "0.85rem",
            padding: "8px 18px",
            minHeight: "38px",
            borderRadius: "10px",
          }}
        >
          Search
        </button>
      </form>

      {state.status === "loading" && <ModuleLoading label="Searching workspace and intelligence..." />}
      {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}

      {state.status === "ready" && (
        <div
          style={{
            display: "grid",
            gap: "24px",
            gridTemplateColumns: activeInvestigation ? "minmax(0, 1fr) 440px" : "minmax(0, 1fr)",
            alignItems: "start",
          }}
        >
          <div style={{ display: "grid", gap: "24px" }}>
            {/* Ask Cogent Action Card (Always Available like Chrome Omnibox) */}
            {initialQuery.length >= 2 && (
              <section
                className="panel cogent-search-action-card"
                style={{
                  background: "linear-gradient(135deg, rgba(42, 75, 255, 0.04), rgba(56, 189, 248, 0.04))",
                  border: "1px solid rgba(42, 75, 255, 0.2)",
                  borderRadius: "14px",
                  padding: "20px 24px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px", marginBottom: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "1.25rem" }}>🔍</span>
                    <h2 style={{ fontSize: "1.1rem", margin: 0 }}>
                      Ask Cogent: &ldquo;{initialQuery}&rdquo;
                    </h2>
                  </div>
                  <button
                    type="button"
                    onClick={() => startCogentInvestigation()}
                    className="primary-button"
                    style={{
                      fontSize: "0.82rem",
                      padding: "8px 16px",
                      borderRadius: "10px",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <span>Investigate with Cogent</span>
                    <span>→</span>
                  </button>
                </div>
                <p style={{ margin: "0 0 12px 0", fontSize: "0.88rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  Launch a bounded intelligence analyst investigation. Cogent will analyze stored evidence, synthesize live external sources if needed, and assess implications through your Company Context.
                </p>

                {state.data.cogent_inquiry?.suggested_angles && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "10px" }}>
                    {state.data.cogent_inquiry.suggested_angles.map((angle, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => startCogentInvestigation(angle)}
                        style={{
                          background: "var(--bg-surface)",
                          border: "1px solid var(--border)",
                          borderRadius: "8px",
                          padding: "6px 12px",
                          fontSize: "0.8rem",
                          color: "var(--text-primary)",
                          cursor: "pointer",
                          textAlign: "left",
                        }}
                      >
                        {angle}
                      </button>
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* Categorized Stored Results */}
            {(() => {
              const groups = [
                {
                  title: "Decision Briefs",
                  items: state.data.briefs,
                  getHref: (item: SearchItem) => `/briefs/${item.id}`,
                },
                {
                  title: "Intelligence",
                  items: state.data.intelligence,
                  getHref: (item: SearchItem) => `/signals/${item.signal_id || item.id}`,
                },
                {
                  title: "Entities",
                  items: state.data.entities,
                  getHref: (item: SearchItem) => `/entities/${item.id}`,
                },
              ];

              const totalCount =
                state.data.briefs.length + state.data.intelligence.length + state.data.entities.length;

              if (!totalCount && initialQuery.length >= 2) {
                return (
                  <section
                    className="panel"
                    style={{
                      padding: "36px",
                      textAlign: "center",
                      background: "var(--bg-surface)",
                      border: "1px solid var(--border)",
                      borderRadius: "14px",
                    }}
                  >
                    <h2 style={{ fontSize: "1.3rem", marginBottom: "8px" }}>
                      No verified stored records match &ldquo;{initialQuery}&rdquo;
                    </h2>
                    <p style={{ color: "var(--text-secondary)", fontSize: "0.92rem", maxWidth: "520px", margin: "0 auto 20px" }}>
                      Stem has not corroborated a stored development matching this keyword yet.
                      You can ask Cogent to investigate live across external sources.
                    </p>
                    <button
                      type="button"
                      onClick={() => startCogentInvestigation()}
                      className="primary-button"
                      style={{ fontSize: "0.88rem", padding: "10px 22px" }}
                    >
                      Investigate Live with Cogent 🔍
                    </button>
                  </section>
                );
              }

              return (
                <div className="search-results">
                  {groups.map(
                    ({ title, items, getHref }) =>
                      items.length > 0 && (
                        <section key={title}>
                          <h2>{title}</h2>
                          {items.map((item) => (
                            <Link className="search-result" href={getHref(item)} key={item.id}>
                              <div>
                                <strong>{item.title}</strong>
                                <p>{item.summary?.replaceAll("_", " ")}</p>
                              </div>
                              <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                                {item.urgency && (
                                  <span className={`priority-chip priority-${item.urgency.toLowerCase()}`} style={{ fontSize: "0.65rem", padding: "3px 7px" }}>
                                    {item.urgency}
                                  </span>
                                )}
                                <span>{item.domain?.replaceAll("_", " ") ?? "View"} →</span>
                              </span>
                            </Link>
                          ))}
                        </section>
                      )
                  )}
                </div>
              );
            })()}
          </div>

          {/* Embedded / Slide-Over Cogent Analyst Investigation Panel */}
          {activeInvestigation && (
            <aside
              style={{
                position: "sticky",
                top: "84px",
                maxHeight: "calc(100vh - 100px)",
                display: "grid",
                gridTemplateRows: "auto minmax(0, 1fr)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border)",
                  borderBottom: "0",
                  borderRadius: "14px 14px 0 0",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span>🔍</span>
                  <strong style={{ fontSize: "0.85rem" }}>Cogent Investigation</strong>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveInvestigation(null)}
                  style={{
                    background: "transparent",
                    border: "0",
                    cursor: "pointer",
                    fontSize: "1.1rem",
                    color: "var(--text-secondary)",
                  }}
                  aria-label="Close analyst panel"
                >
                  ✕
                </button>
              </div>
              <CILPanel
                anchorId="00000000-0000-0000-0000-000000000000"
                anchorType="COMPANY_LENS"
                initialPrompt={activeInvestigation.prompt}
                suggestedInquiries={activeInvestigation.suggested}
              />
            </aside>
          )}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <WorkspaceShell>
      <section className="content-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Decision Intelligence Search</p>
            <h1>Search & Ask Cogent</h1>
            <p>
              Search verified intelligence across your permitted workspace data or launch a bounded analyst investigation with Cogent.
            </p>
          </div>
        </div>
        <Suspense fallback={<ModuleLoading label="Loading search..." />}>
          <Results />
        </Suspense>
      </section>
    </WorkspaceShell>
  );
}
