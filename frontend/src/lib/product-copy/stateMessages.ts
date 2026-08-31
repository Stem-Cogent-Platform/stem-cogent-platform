export const stateMessages = {
  briefingEmpty: {
    title: "No decisions need your attention right now.",
    body: "Stem is still monitoring your company, Focus Areas, and the wider market."
  },
  alertsEmpty: {
    title: "No alerts right now.",
    body: "Stem will notify you when a Decision Brief crosses your configured delivery threshold."
  },
  digestEmpty: {
    title: "Your next briefing",
    body: "Your digest will bring together decisions requiring attention, watched briefs, and important Focus Area changes."
  },
  companyBriefsEmpty: {
    title: "No company decisions need attention.",
    body: "Stem will surface a Decision Brief when verified evidence materially affects your Company Context."
  },
  watchlistEmpty: "Add Company Context to focus monitoring on the organisations and infrastructure that matter to you.",
  focusEmpty: "Add a Focus Area to make your personal briefing more precise.",
  genericError: "We couldn't load this view. Try again."
} as const;

export function friendlyError(error: unknown, fallback: string = stateMessages.genericError) {
  if (!(error instanceof Error)) return fallback;
  const lower = error.message.toLowerCase();
  if (lower.includes("network") || lower.includes("reach")) return "Stem couldn't connect. Check your connection and try again.";
  if (lower.includes("timeout") || lower.includes("too long")) return "This is taking longer than expected. Try again.";
  return fallback;
}
