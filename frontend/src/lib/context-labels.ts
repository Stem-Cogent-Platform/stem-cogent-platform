export function parseContextList(value: unknown): string[] {
  const labels = new Map<string, string>();
  for (const fragment of String(value ?? "").split(/[,;\n]+/)) {
    const label = fragment.trim().replace(/^(?:and|&)\s+/i, "").replace(/\s+/g, " ").trim();
    if (label && !labels.has(label.toLowerCase())) labels.set(label.toLowerCase(), label);
  }
  return [...labels.values()];
}
