export function StemMark({ compact = false }: { compact?: boolean }) {
  return (
    <span className={compact ? "stem-mark stem-mark-compact" : "stem-mark"} aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
    </span>
  );
}
