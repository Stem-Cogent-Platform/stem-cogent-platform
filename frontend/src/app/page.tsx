import Link from "next/link";

import { LegalConsentCard } from "@/components/legal-consent-card";
import { StemMark } from "@/components/stem-mark";

const steps = ["Account", "Legal", "Company context", "Decision lens", "Focus areas"];

export default function HomePage() {
  return (
    <main className="onboarding-page">
      <header className="site-header">
        <Link className="wordmark" href="/" aria-label="Stem home">
          <StemMark />
          <span>Stem</span>
        </Link>
        <p className="header-note">Structured. Fluid. Cogent.</p>
        <Link className="secondary-button" href="/login">Sign in</Link>
      </header>

      <section className="onboarding-layout" aria-labelledby="onboarding-title">
        <aside className="onboarding-intro">
          <p className="eyebrow">Secure workspace setup</p>
          <h1 id="onboarding-title">Build clarity on a trusted foundation.</h1>
          <p className="intro-copy">
            Before company information is unlocked, review how Stem processes and
            isolates the information you are authorised to provide.
          </p>
          <ol className="step-list" aria-label="Onboarding progress">
            {steps.map((step, index) => (
              <li className={index === 1 ? "is-current" : index < 1 ? "is-complete" : ""} key={step}>
                <span>{index + 1}</span>
                <div>
                  <strong>{step}</strong>
                  {index === 1 && <small>Current step</small>}
                </div>
              </li>
            ))}
          </ol>
        </aside>

        <LegalConsentCard />
      </section>
    </main>
  );
}
