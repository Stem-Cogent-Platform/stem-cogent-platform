"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { apiRequest } from "@/lib/api";

const roles = [
  ["CEO", "Founder / CEO"],
  ["CSO", "Strategy"],
  ["COO", "Operations"],
  ["CFO", "Finance"],
  ["PRODUCT", "Product"],
  ["GROWTH", "Growth"],
  ["COMPLIANCE_RISK", "Compliance / Risk"],
  ["RESEARCH", "Research"]
] as const;

function list(value: FormDataEntryValue | null) {
  return String(value ?? "").split(",").map((item) => item.trim()).filter(Boolean).slice(0, 5);
}

export function DecisionLensForm() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest("/me/decision-lens", {
        method: "PUT",
        body: JSON.stringify({
          role_code: form.get("role"),
          responsibility_tags: list(form.get("responsibilities")),
          priority_domains: list(form.get("priorities")),
          delivery_preference: form.get("delivery")
        })
      });
      const focus = String(form.get("focus") ?? "").trim();
      if (focus) {
        await apiRequest("/me/focus-areas", {
          method: "POST",
          body: JSON.stringify({ focus_type: "TOPIC", label: focus, query_text: focus, weight: 1 })
        });
      }
      setMessage("Your Decision Lens is ready. Opening your briefing…");
      window.setTimeout(() => router.push("/briefing"), 500);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "We could not save your lens. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="context-form" onSubmit={submit}>
      <fieldset>
        <legend>Your role</legend>
        <div className="role-grid">
          {roles.map(([value, label], index) => (
            <label className="role-option" key={value}>
              <input defaultChecked={index === 0} name="role" type="radio" value={value} />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <div className="field-grid">
        <label><span>Responsibilities</span><input name="responsibilities" placeholder="Capital allocation, Partnerships" /></label>
        <label><span>Priority domains (up to five)</span><input name="priorities" placeholder="Regulatory policy, Infrastructure" required /></label>
        <label><span>First Focus Area</span><input name="focus" placeholder="NIBSS reliability" /></label>
        <label><span>Delivery preference</span><select defaultValue="IMPORTANT_AND_CRITICAL" name="delivery"><option value="CRITICAL_ONLY">Critical only</option><option value="IMPORTANT_AND_CRITICAL">Important + Critical</option><option value="DAILY_BRIEFING">Daily briefing</option><option value="WEEKLY_BRIEFING">Weekly briefing</option></select></label>
      </div>
      {message && <p className="form-message">{message}</p>}
      <div className="form-footer"><span /><button className="primary-button" disabled={saving} type="submit">{saving ? "Saving lens…" : "Complete setup"}</button></div>
    </form>
  );
}
