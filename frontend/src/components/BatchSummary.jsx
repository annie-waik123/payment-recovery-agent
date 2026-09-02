import { getTopEntry, mostSuccessfulIntervention, computeAIDiagnosticsStats, formatPaise } from "../utils/audit";

function labelize(key) {
  if (!key) return null;
  return key
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

/**
 * Plain-template executive summary. Highlights failure distribution, top
 * intervention outcomes, and AI forensic investigation of unclassified failures.
 */

export default function BatchSummary({ metrics, audit, payments }) {
  if (!metrics) return null;

  const topCause = getTopEntry(metrics.root_cause_breakdown);
  const bestIntervention = mostSuccessfulIntervention(audit);
  const pct = metrics.recovery_rate !== undefined ? (metrics.recovery_rate * 100).toFixed(0) : null;
  const recoveredCount = metrics.recovered_count ?? 0;
  const aiStats = computeAIDiagnosticsStats(audit, metrics, payments);

  const aiSummary =
    aiStats.aiDiagnosesCount > 0
      ? `AI investigated ${aiStats.aiDiagnosesCount} previously unclassified failure${
          aiStats.aiDiagnosesCount === 1 ? "" : "s"
        }, providing forensic analysis and safe fallback recommendations where deterministic rules could not identify a root cause${
          aiStats.recoveredRevenuePaise > 0
            ? ` (recovering ${formatPaise(aiStats.recoveredRevenuePaise)} in revenue).`
            : "."
        }`
      : null;


  const clauses = [
    metrics.total_payments !== undefined
      ? `${metrics.total_payments} failed payment${metrics.total_payments === 1 ? "" : "s"} analyzed.`
      : null,
    topCause ? `Most common failure: ${labelize(topCause[0])}.` : null,
    bestIntervention
      ? `Most successful intervention: ${labelize(bestIntervention.name)} (${bestIntervention.successes}/${bestIntervention.attempts} recovered).`
      : null,
    `${recoveredCount} payment${recoveredCount === 1 ? "" : "s"} recovered.`,
    pct !== null ? `${pct}% recovery rate.` : null,
    aiSummary,
  ].filter(Boolean);

  return (
    <section className="batch-summary-panel">
      <div className="section-label">Executive Batch Summary</div>
      <p className="batch-summary-text">{clauses.join(" ")}</p>
    </section>
  );
}
