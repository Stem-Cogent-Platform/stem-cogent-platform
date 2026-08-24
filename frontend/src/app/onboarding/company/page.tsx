import Link from "next/link";

import { CompanyContextForm } from "@/components/company-context-form";
import { StemMark } from "@/components/stem-mark";

export default function CompanyOnboardingPage() {
  return (
    <main className="form-page">
      <header className="site-header"><Link className="wordmark" href="/"><StemMark /><span>Stem</span></Link><span className="step-chip">Step 3 of 5</span></header>
      <section className="form-card">
        <p className="eyebrow">Company context</p>
        <h1>What should Stem understand about the business?</h1>
        <p className="card-intro">A concise context improves relevance without changing the factual evidence underneath.</p>
        <CompanyContextForm />
      </section>
    </main>
  );
}
