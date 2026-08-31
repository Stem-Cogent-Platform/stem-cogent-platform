import Link from "next/link";

import { LegalConsentCard } from "@/components/legal-consent-card";
import { StemMark } from "@/components/stem-mark";

export default function LegalOnboardingPage() {
  return (
    <main className="form-page onboarding-legal-page">
      <header className="site-header">
        <Link className="wordmark" href="/briefing"><StemMark /><span>Stem Cogent</span></Link>
        <span className="step-chip">Step 1 of 6</span>
      </header>
      <section className="legal-onboarding-wrap">
        <div className="legal-onboarding-intro">
          <p className="eyebrow">Workspace protection</p>
          <h1>Review the legal foundation once.</h1>
          <p>Legal acceptance belongs inside authenticated onboarding—not on the public homepage.</p>
        </div>
        <LegalConsentCard />
      </section>
    </main>
  );
}
