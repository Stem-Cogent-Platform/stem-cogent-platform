"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError, apiRequest } from "@/lib/api";

function values(value: FormDataEntryValue | null) {
  return String(value ?? "").split(",").map((item) => item.trim()).filter(Boolean);
}

export function CompanyContextForm() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest("/context/company", {
        method: "PUT",
        body: JSON.stringify({
          business_categories: values(form.get("categories")),
          operating_markets: values(form.get("markets")),
          customer_segments: values(form.get("segments")),
          regulatory_categories: values(form.get("regulatory")),
          strategic_priorities: values(form.get("priorities"))
        })
      });
      setMessage("Company Context saved. Next, shape your Decision Lens.");
      window.setTimeout(() => router.push("/onboarding/lens"), 500);
    } catch (error) {
      if (error instanceof ApiError && error.code === "LEGAL_CONSENT_REQUIRED") {
        setMessage("Legal acceptance is required first. Return to the previous step to continue.");
      } else {
        setMessage(error instanceof Error ? error.message : "We could not save this context. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="context-form" onSubmit={submit}>
      <div className="field-grid">
        <label><span>Fintech categories</span><input name="categories" placeholder="Payments, Lending" required /></label>
        <label><span>Operating markets</span><input defaultValue="NG" name="markets" required /></label>
        <label><span>Customer segments</span><input name="segments" placeholder="SME merchants, Banks" /></label>
        <label><span>Regulatory categories</span><input name="regulatory" placeholder="Payment service, Consumer credit" /></label>
        <label className="full-field"><span>Strategic priorities</span><input name="priorities" placeholder="Settlement resilience, Margin, Expansion" required /></label>
      </div>
      <p className="field-help">Separate multiple entries with commas. Keep this focused on information you are authorised to provide.</p>
      {message && <p className="form-message">{message}</p>}
      <div className="form-footer"><span /><button className="primary-button" disabled={saving} type="submit">{saving ? "Saving context…" : "Save and continue"}</button></div>
    </form>
  );
}
