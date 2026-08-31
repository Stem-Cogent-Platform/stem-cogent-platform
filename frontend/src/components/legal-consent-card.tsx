"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { ApiError, apiRequest, bootstrapSession } from "@/lib/api";

type LegalDocument = {
  code: string;
  title: string;
  version: string;
  body: string;
  acceptance_text: string;
  sha256: string;
};

type LegalBundle = {
  application_version: string;
  regulatory_framework: {
    primary_law: string;
    regulator: string;
    implementation_directive: string;
  };
  documents: LegalDocument[];
};

const friendlyFallback =
  "We could not load the legal documents right now. Your workspace is safe; please try again in a few minutes.";

export function LegalConsentCard() {
  const router = useRouter();
  const [bundle, setBundle] = useState<LegalBundle | null>(null);
  const [checks, setChecks] = useState({ terms: false, privacy: false, ndpa: false });
  const [state, setState] = useState<"loading" | "ready" | "saving" | "error" | "saved">("loading");
  const [message, setMessage] = useState("");

  async function loadDocuments() {
    setState("loading");
    setMessage("");
    try {
      if (!(await bootstrapSession())) {
        router.replace("/login?next=%2Fonboarding%2Flegal");
        return;
      }
      const result = await apiRequest<LegalBundle>("/api/v1/compliance/documents");
      setBundle(result);
      setState("ready");
    } catch {
      setState("error");
      setMessage(friendlyFallback);
    }
  }

  useEffect(() => {
    let active = true;
    void bootstrapSession()
      .then((authenticated) => {
        if (!authenticated) {
          router.replace("/login?next=%2Fonboarding%2Flegal");
          throw new ApiError("Your session has ended", 401);
        }
        return apiRequest<LegalBundle>("/api/v1/compliance/documents");
      })
      .then((result) => {
        if (!active) return;
        setBundle(result);
        setState("ready");
      })
      .catch(() => {
        if (!active) return;
        setState("error");
        setMessage(friendlyFallback);
      });
    return () => {
      active = false;
    };
  }, [router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!bundle || !checks.terms || !checks.privacy || !checks.ndpa) return;
    const documents = Object.fromEntries(bundle.documents.map((document) => [document.code, document]));
    setState("saving");
    setMessage("");
    try {
      await apiRequest("/api/v1/compliance/consent", {
        method: "POST",
        body: JSON.stringify({
          idempotency_key: crypto.randomUUID(),
          terms_accepted: true,
          privacy_notice_acknowledged: true,
          ndpa_consent_granted: true,
          terms_version: documents.TERMS_OF_SERVICE.version,
          privacy_policy_version: documents.PRIVACY_NOTICE.version,
          ndpa_consent_version: documents.NDPA_CONSENT.version,
          application_version: bundle.application_version
        })
      });
      setState("saved");
      setMessage("Your acceptance is securely recorded. Company Context is now available.");
      window.setTimeout(() => router.push("/onboarding"), 500);
    } catch (error) {
      setState("ready");
      if (error instanceof ApiError && error.status === 401) {
        setMessage("Your session has ended. Sign in again, then return to this step.");
      } else {
        setMessage(error instanceof Error ? error.message : friendlyFallback);
      }
    }
  }

  if (state === "loading") {
    return (
      <section className="consent-card" aria-live="polite">
        <p className="eyebrow">Legal consent</p>
        <h2>Preparing the current documents…</h2>
        <div className="document-skeleton" />
        <div className="document-skeleton short" />
      </section>
    );
  }

  if (state === "error" || !bundle) {
    return (
      <section className="consent-card module-failure" role="status">
        <p className="eyebrow">Legal consent</p>
        <h2>This step is temporarily resting.</h2>
        <p>{message || friendlyFallback}</p>
        <button className="secondary-button" onClick={() => void loadDocuments()} type="button">
          Try again
        </button>
      </section>
    );
  }

  const byCode = Object.fromEntries(bundle.documents.map((document) => [document.code, document]));
  return (
    <section className="consent-card">
      <div className="card-heading">
        <div>
          <p className="eyebrow">Legal consent</p>
          <h2>Review before adding company information</h2>
        </div>
        <span className="verified-chip">Version controlled</span>
      </div>
      <p className="card-intro">
        Acceptance is recorded with your user, tenant, time, source address, document versions,
        and a server signature. It cannot be edited later.
      </p>

      <form onSubmit={submit}>
        <label className="consent-row">
          <input
            checked={checks.terms}
            onChange={(event) => setChecks({ ...checks, terms: event.target.checked })}
            type="checkbox"
          />
          <span>
            <strong>{byCode.TERMS_OF_SERVICE.acceptance_text}</strong>
            <small><Link href="/legal/terms" target="_blank">Read Terms of Service</Link></small>
          </span>
        </label>
        <label className="consent-row">
          <input
            checked={checks.privacy}
            onChange={(event) => setChecks({ ...checks, privacy: event.target.checked })}
            type="checkbox"
          />
          <span>
            <strong>{byCode.PRIVACY_NOTICE.acceptance_text}</strong>
            <small><Link href="/legal/privacy" target="_blank">Read Privacy Notice</Link></small>
          </span>
        </label>
        <label className="consent-row consent-row-emphasis">
          <input
            checked={checks.ndpa}
            onChange={(event) => setChecks({ ...checks, ndpa: event.target.checked })}
            type="checkbox"
          />
          <span>
            <strong>{byCode.NDPA_CONSENT.acceptance_text}</strong>
            <small>{bundle.regulatory_framework.primary_law} · {bundle.regulatory_framework.implementation_directive}</small>
          </span>
        </label>

        {message && <p className={state === "saved" ? "form-message success" : "form-message"}>{message}</p>}
        <div className="form-footer">
          <p>Company fields remain locked until all three acknowledgements are recorded.</p>
          <button
            className="primary-button"
            disabled={!checks.terms || !checks.privacy || !checks.ndpa || state === "saving"}
            type="submit"
          >
            {state === "saving" ? "Recording acceptance…" : "Accept and continue"}
          </button>
        </div>
      </form>
    </section>
  );
}
