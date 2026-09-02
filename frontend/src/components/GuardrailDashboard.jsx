import { computeGuardrailStats } from "../utils/audit";

const REASON_LABELS = {
  max_retries: "Max retries reached",
  low_confidence: "Low confidence",
  cooldown: "Cooldown window",
  spend_cap: "Batch spend cap",
  action_cap: "Batch action cap",
  other: "Other",
};

export default function GuardrailDashboard({ records }) {
  const stats = computeGuardrailStats(records);
  const reasonEntries = Object.entries(stats.overrideReasons).sort((a, b) => b[1] - a[1]);

  return (
    <section className="chart-panel guardrail-panel">
      <div className="audit-header">
        <h2 className="chart-title">Guardrail Agent</h2>
        <span className="audit-count mono">{stats.total} checks</span>
      </div>

      {stats.total === 0 ? (
        <div className="chart-empty">No guardrail checks recorded yet.</div>
      ) : (
        <>
          <div className="guardrail-stat-row">
            <div className="guardrail-stat">
              <div className="stat-label">Total Checks</div>
              <div className="stat-value stat-value-mono">{stats.total}</div>
            </div>
            <div className="guardrail-stat" style={{ "--card-accent": "var(--c-recovered)" }}>
              <div className="stat-label">Approved</div>
              <div className="stat-value stat-value-mono" style={{ color: "var(--c-recovered)" }}>
                {stats.approved}
              </div>
            </div>
            <div className="guardrail-stat" style={{ "--card-accent": "var(--c-warning)" }}>
              <div className="stat-label">Overridden</div>
              <div className="stat-value stat-value-mono" style={{ color: "var(--c-warning)" }}>
                {stats.overridden}
              </div>
            </div>
            <div className="guardrail-stat" style={{ "--card-accent": "var(--c-pending)" }}>
              <div className="stat-label">Override %</div>
              <div className="stat-value stat-value-mono">
                {stats.overridePct !== null ? `${stats.overridePct.toFixed(1)}%` : "—"}
              </div>
            </div>
          </div>

          <div className="guardrail-bar-track" title={`${stats.approved} approved · ${stats.overridden} overridden`}>
            <div
              className="guardrail-bar-approved"
              style={{ width: `${(stats.approved / stats.total) * 100}%` }}
            />
            <div
              className="guardrail-bar-overridden"
              style={{ width: `${(stats.overridden / stats.total) * 100}%` }}
            />
          </div>

          {reasonEntries.length > 0 && (
            <div className="guardrail-reasons">
              <div className="section-label" style={{ marginTop: 16 }}>
                Override Reasons
              </div>
              <div className="guardrail-reason-list">
                {reasonEntries.map(([reason, count]) => (
                  <div className="guardrail-reason-row" key={reason}>
                    <span>{REASON_LABELS[reason] || reason}</span>
                    <span className="mono">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
