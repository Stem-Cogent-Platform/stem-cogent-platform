import Link from "next/link";

import { DecisionLensForm } from "@/components/decision-lens-form";
import { StemMark } from "@/components/stem-mark";

export default function LensOnboardingPage() {
  return (
    <main className="form-page">
      <header className="site-header"><Link className="wordmark" href="/"><StemMark /><span>Stem</span></Link><span className="step-chip">Steps 4–5 of 5</span></header>
      <section className="form-card">
        <p className="eyebrow">Your Decision Lens</p>
        <h1>What should Stem prioritise for you?</h1>
        <p className="card-intro">Your role and Focus Areas shape ranking and framing. They never alter the underlying facts.</p>
        <DecisionLensForm />
      </section>
    </main>
  );
}
