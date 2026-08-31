import { BriefCard } from "@/components/brief-card";
import { Brief } from "@/lib/types";

export function PriorityAlertMatrix({ briefs }: { briefs: Brief[] }) {
  const critical = briefs.filter((brief) => (brief.urgency_band ?? brief.relevance_band) === "CRITICAL");
  const high = briefs.filter((brief) => (brief.urgency_band ?? brief.relevance_band) === "HIGH");
  if (!critical.length && !high.length) return null;

  return <section aria-label="Priority alert matrix" className="priority-matrix">
    <div className="section-heading"><h2>Priority alert matrix</h2><span>Immediate review</span></div>
    <div className="priority-matrix-grid">
      <div><header><strong>Critical</strong><span>{critical.length}</span></header>{critical.map((brief) => <BriefCard brief={brief} key={brief.id} />)}{!critical.length && <p className="matrix-clear">No critical briefs.</p>}</div>
      <div><header><strong>High</strong><span>{high.length}</span></header>{high.map((brief) => <BriefCard brief={brief} key={brief.id} />)}{!high.length && <p className="matrix-clear">No high-priority briefs.</p>}</div>
    </div>
  </section>;
}
