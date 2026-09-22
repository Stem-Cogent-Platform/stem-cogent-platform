"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { WorkspaceShell } from "@/components/workspace-shell";

export default function WatchlistPage() {
  const router = useRouter();

  useEffect(() => {
    const timer = window.setTimeout(() => {
      router.replace("/company");
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [router]);

  return (
    <WorkspaceShell>
      <section className="content-page">
        <div
          className="state-card"
          style={{
            maxWidth: "680px",
            margin: "40px auto",
            textAlign: "center",
            padding: "48px 36px",
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "18px",
          }}
        >
          <p className="eyebrow" style={{ color: "var(--accent)", marginBottom: "12px" }}>
            Monitoring Scope Update
          </p>
          <h1 style={{ fontSize: "2.2rem", marginBottom: "16px", letterSpacing: "-0.04em" }}>
            Watchlist Is Now Automated
          </h1>
          <p
            style={{
              fontSize: "1.02rem",
              color: "var(--text-secondary)",
              lineHeight: 1.65,
              marginBottom: "28px",
              maxWidth: "540px",
              marginLeft: "auto",
              marginRight: "auto",
            }}
          >
            In Stem Cogent, you no longer have to maintain a separate manual watchlist.
            Your continuous monitoring scope is automatically maintained by:
            <br />
            <strong style={{ color: "var(--text-primary)", display: "block", margin: "10px 0", fontSize: "1.08rem" }}>
              Company Context + Focus Areas = Monitoring Scope
            </strong>
            Redirecting you to your active company scope...
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: "14px", flexWrap: "wrap" }}>
            <Link className="primary-button" href="/company" style={{ display: "inline-flex", alignItems: "center" }}>
              Go to Company Scope →
            </Link>
            <Link className="secondary-button" href="/briefing" style={{ display: "inline-flex", alignItems: "center" }}>
              My Decision Briefing
            </Link>
          </div>
        </div>
      </section>
    </WorkspaceShell>
  );
}
