"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";

function Completion() {
  const reference = useSearchParams().get("reference");
  const [status, setStatus] = useState<"loading" | "succeeded" | "pending" | "error">(
    reference ? "loading" : "error"
  );
  const [message, setMessage] = useState(
    reference
      ? "Confirming your transaction with Paystack…"
      : "No checkout reference provided. Return to settings to manage your subscription."
  );

  useEffect(() => {
    if (!reference) return;
    void apiRequest<{ status: string }>(
      `/api/v1/billing/checkout/${encodeURIComponent(reference)}`
    )
      .then((result) => {
        if (result.status === "SUCCEEDED") {
          setStatus("succeeded");
          setMessage("Payment confirmed! Your enterprise workspace is active.");
        } else {
          setStatus("pending");
          setMessage("Paystack is still processing the settlement. Your subscription will activate momentarily.");
        }
      })
      .catch((error) => {
        setStatus("error");
        setMessage(
          error instanceof Error ? error.message : "Payment confirmation was delayed."
        );
      });
  }, [reference]);

  return (
    <WorkspaceShell>
      <section className="content-page" style={{ maxWidth: 640, margin: "40px auto" }}>
        <article className="consent-card" style={{ padding: 32, textAlign: "center" }}>
          <div style={{ display: "inline-block", marginBottom: 16 }}>
            {status === "succeeded" && (
              <span style={{ fontSize: 40, lineHeight: 1 }}>✅</span>
            )}
            {status === "loading" && (
              <span style={{ fontSize: 40, lineHeight: 1 }}>⏳</span>
            )}
            {status === "pending" && (
              <span style={{ fontSize: 40, lineHeight: 1 }}>🔄</span>
            )}
            {status === "error" && (
              <span style={{ fontSize: 40, lineHeight: 1 }}>⚠️</span>
            )}
          </div>
          <p className="eyebrow" style={{ textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Payment Settlement
          </p>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, margin: "12px 0 16px" }}>
            {message}
          </h1>
          {reference && (
            <p style={{ fontSize: "0.85rem", opacity: 0.7, marginBottom: 24, fontFamily: "monospace" }}>
              Ref: {reference}
            </p>
          )}
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap", marginTop: 24 }}>
            <Link className="primary-button" href="/radar">
              Go to Live Radar →
            </Link>
            <Link
              href="/settings"
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "8px 16px",
                borderRadius: 6,
                border: "1px solid rgba(255, 255, 255, 0.15)",
                color: "inherit",
                textDecoration: "none",
                fontSize: "0.9rem",
              }}
            >
              Subscription & Settings
            </Link>
          </div>
        </article>
      </section>
    </WorkspaceShell>
  );
}

export default function BillingCompletePage() {
  return (
    <Suspense fallback={<main className="content-page">Confirming payment…</main>}>
      <Completion />
    </Suspense>
  );
}
