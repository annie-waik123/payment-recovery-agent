import { getTopEntry, computeExecutorStats, computeGuardrailStats, computeDecisionStats } from "../utils/audit";

function labelize(key) {
  if (!key) return "—";
  return key
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

function AgentCard({ title, accent, rows }) {
  return (
    <div className="agent-card" style={{ "--card-accent": accent }}>
      <div className="agent-card-title">{title}</div>
      <div className="agent-card-rows">
        {rows.map(([label, value]) => (
          <div className="agent-card-row" key={label}>
            <span className="muted">{label}</span>
            <span className="mono">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * One card per pipeline agent. Root-cause and intervention totals come
 * from /metrics (already-aggregated, authoritative counts); executor and
 * guardrail numbers are derived from the audit trail since /metrics
 * doesn't break those down by outcome.
 */
export default function AgentPerformanceCards({ metrics, audit }) {
  const topCause = getTopEntry(metrics?.root_cause_breakdown);

  // Decision Agent's own output — from decide-stage audit entries, before
  // guardrails.py can override them. See computeDecisionStats for why
  // metrics.intervention_breakdown is the wrong source for this card.
  const decisionCounts = computeDecisionStats(audit);
  const retryDecisions = (decisionCounts.retry_now || 0) + (decisionCounts.retry_later || 0);
  const altRecommendations = decisionCounts.suggest_alt_method || 0;

  const executorStats = computeExecutorStats(audit);
  const guardrailStats = computeGuardrailStats(audit);

  return (
    <section className="agent-performance-section">
      <div className="section-label">Agent Performance</div>
      <div className="agent-performance-grid">
        <AgentCard
          title="Diagnose Agent"
          accent="var(--c-info)"
          rows={[
            ["Payments Analyzed", metrics?.total_payments ?? "—"],
            ["Top Root Cause", topCause ? labelize(topCause[0]) : "—"],
          ]}
        />
        <AgentCard
          title="Decision Agent"
          accent="var(--c-decide)"
          rows={[
            ["Retry Decisions", retryDecisions],
            ["Alt-Method Suggestions", altRecommendations],
          ]}
        />
        <AgentCard
          title="Guardrail Agent"
          accent="var(--c-pending)"
          rows={[
            ["Approvals", guardrailStats.approved],
            ["Overrides", guardrailStats.overridden],
          ]}
        />
        <AgentCard
          title="Executor Agent"
          accent="var(--c-recovered)"
          rows={[
            ["Successful Recoveries", executorStats.recovered],
            ["Failed Recoveries", executorStats.still_failing + executorStats.unrecoverable],
          ]}
        />
      </div>
    </section>
  );
}
