"use client";

import { useCallback, useEffect, useState } from "react";

import { ModuleFailure, ModuleLoading } from "@/components/module-state";
import { WorkspaceShell } from "@/components/workspace-shell";
import { apiRequest } from "@/lib/api";
import { LoadState } from "@/lib/types";

type Plan = { plan_code: string; name: string; monthly_price_cents: number | null };
type Billing = { plan_code: string; billing_status: string };

export default function BillingPage() {
  const [state, setState] = useState<LoadState<{ plans: Plan[]; billing: Billing }>>({ status: "loading" });
  const [message, setMessage] = useState("");
  const [pendingPlan, setPendingPlan] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const [plans, billing] = await Promise.all([
        apiRequest<Plan[]>("/api/v1/billing/plans"),
        apiRequest<Billing>("/api/v1/billing/status")
      ]);
      setState({ status: "ready", data: { plans, billing } });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Billing could not be loaded." });
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function checkout(planCode: string) {
    setMessage("");
    setPendingPlan(planCode);
    try {
      const result = await apiRequest<{ authorization_url: string }>("/api/v1/billing/checkout", {
        method: "POST",
        body: JSON.stringify({ plan_code: planCode, idempotency_key: crypto.randomUUID() })
      });
      window.location.assign(result.authorization_url);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Paystack checkout could not be started. Try again in a few minutes.");
      setPendingPlan(null);
    }
  }

  return (
    <WorkspaceShell>
      <section className="content-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Server-enforced access</p>
            <h1>Plans &amp; billing</h1>
            <p>Plans are displayed in USD. Checkout locks the current official CBN USD/NGN reference rate before Paystack charges the quoted Naira amount. Stem never stores card details.</p>
          </div>
        </div>
        {state.status === "loading" && <ModuleLoading label="Loading billing status and plans" />}
        {state.status === "error" && <ModuleFailure message={state.message} retry={() => void load()} />}
        {state.status === "ready" && <>
          <p className="current-plan">Current plan: <strong>{state.data.billing.plan_code}</strong> · {state.data.billing.billing_status}</p>
          <div className="plan-grid">
            {state.data.plans.filter((plan) => plan.plan_code !== "TRIAL").map((plan) => {
              const current = state.data.billing.plan_code === plan.plan_code && state.data.billing.billing_status === "ACTIVE";
              const pending = pendingPlan === plan.plan_code;
              return <article key={plan.plan_code}>
                <p className="eyebrow">{plan.plan_code}</p>
                <h2>{plan.name}</h2>
                <strong className="plan-price">{plan.monthly_price_cents ? `$${(plan.monthly_price_cents / 100).toLocaleString()}` : "Custom"}<small>{plan.monthly_price_cents ? "/month" : ""}</small></strong>
                {plan.monthly_price_cents ? <>
                  <p className="plan-settlement-note">Charged in NGN at the official CBN reference rate quoted when you continue. Each renewal is quoted again at checkout.</p>
                  <button className="primary-button" disabled={current || pendingPlan !== null} onClick={() => void checkout(plan.plan_code)} type="button">{current ? "Current plan" : pending ? "Opening Paystack…" : "Continue to Paystack"}</button>
                </> : <a className="secondary-button" href="mailto:pilot@stem-cogent.com">Contact pilot team</a>}
              </article>;
            })}
          </div>
          {message && <p className="form-message" role="alert">{message}</p>}
        </>}
      </section>
    </WorkspaceShell>
  );
}
