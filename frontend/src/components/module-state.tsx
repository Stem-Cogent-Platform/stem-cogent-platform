export function ModuleFailure({ message, retry }: { message?: string; retry: () => void }) {
  return (
    <section className="module-failure" role="status">
      <h3>This feature is temporarily resting.</h3>
      <p>{message ?? "We could not load this section. The rest of your workspace is still available."}</p>
      <button className="secondary-button" onClick={retry} type="button">Try again</button>
    </section>
  );
}

export function ModuleLoading({ label = "Loading this section" }: { label?: string }) {
  return <section className="module-loading" aria-label={label} aria-live="polite" role="status"><span className="sr-only">{label}</span><i /><i /><i /><i /><i /></section>;
}
