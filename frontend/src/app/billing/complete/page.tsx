"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";

function Completion() {
  const reference = useSearchParams().get("reference");
  const [message, setMessage] = useState(
    reference
      ? "Confirming your secure payment…"
      : "This checkout link is incomplete. Return to billing to try again."
  );

  useEffect(() => {
    if (!reference) return;
    void apiRequest<{ status: string }>(
      `/api/v1/billing/checkout/${encodeURIComponent(reference)}`
    )
      .then((result) =>
        setMessage(
          result.status === "SUCCEEDED"
            ? "Payment confirmed. Your workspace plan is active."
            : "Paystack is still confirming the transaction. Check again in a moment."
        )
      )
      .catch((error) =>
        setMessage(
          error instanceof Error ? error.message : "Payment confirmation is delayed."
        )
      );
  }, [reference]);

  return (
    <WorkspaceShell>
      <section className="content-page">
        <article className="consent-card">
          <p className="eyebrow">Payment confirmation</p>
          <h1>{message}</h1>
          <Link className="primary-button" href="/settings/billing">
            Return to billing
          </Link>
        </article>
      </section>
    </WorkspaceShell>
  );
}

export default function BillingCompletePage() {
  return (
    <Suspense fallback={<main>Confirming payment…</main>}>
      <Completion />
    </Suspense>
  );
}
