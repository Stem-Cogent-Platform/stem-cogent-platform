"use client";

import { useEffect } from "react";

export default function ErrorBoundary({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Workspace view failed", { digest: error.digest });
  }, [error]);

  return (
    <main className="centered-state">
      <section className="state-card" role="alert">
        <p className="eyebrow">Workspace</p>
        <h1>We could not open this view.</h1>
        <p>Your information is safe. Try the view again without leaving your workspace.</p>
        <button className="primary-button" onClick={reset} type="button">Try again</button>
      </section>
    </main>
  );
}
