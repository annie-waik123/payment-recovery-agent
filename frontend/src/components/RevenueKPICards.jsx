import { formatPaise } from "../utils/audit";

function Kpi({ label, value, sub, accent }) {
  return (
    <div className="stat-card kpi-card" style={{ "--card-accent": accent }}>
      <div className="stat-label">{label}</div>
      <div className="stat-value stat-value-mono">{value ?? "—"}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

/**
 * Revenue at risk / recovered need payment amounts, which this dashboard's
 * current /metrics response doesn't return. These two read optional fields
 * (revenue_at_risk_paise, revenue_recovered_paise) and degrade gracefully
 * to "—" until the backend adds them. Average Retry Success needs no
 * backend change — it's derived client-side from the audit trail.
 */
export default function RevenueKPICards({ metrics, avgRetrySuccess }) {
  const atRisk = metrics?.revenue_at_risk_paise;
  const recovered = metrics?.revenue_recovered_paise;
  const hasRevenueData = atRisk !== undefined && recovered !== undefined;
  const revenuePct = hasRevenueData && atRisk > 0 ? (recovered / atRisk) * 100 : null;

  return (
    <section className="kpi-section">
      <div className="section-label">Revenue Impact</div>
      <div className="stats-grid">
        <Kpi
          label="Revenue at Risk"
          value={hasRevenueData ? formatPaise(atRisk) : "—"}
          sub={!hasRevenueData ? "backend: add revenue_at_risk_paise to /metrics" : null}
          accent="var(--c-unrecoverable)"
        />
        <Kpi
          label="Revenue Recovered"
          value={hasRevenueData ? formatPaise(recovered) : "—"}
          sub={!hasRevenueData ? "backend: add revenue_recovered_paise to /metrics" : null}
          accent="var(--c-recovered)"
        />
        <Kpi
          label="Recovery Revenue %"
          value={revenuePct !== null ? `${revenuePct.toFixed(1)}%` : "—"}
          accent="var(--c-primary)"
        />
        <Kpi
          label="Avg Retry Success"
          value={avgRetrySuccess !== null ? `${(avgRetrySuccess * 100).toFixed(1)}%` : "—"}
          sub="retry_now + retry_later only"
          accent="var(--c-info)"
        />
      </div>
    </section>
  );
}
