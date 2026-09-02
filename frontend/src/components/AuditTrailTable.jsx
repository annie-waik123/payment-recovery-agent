import { useState, useMemo } from "react";
import { Zap, ShieldAlert, CheckCircle2 } from "lucide-react";
import {
  stageMeta,
  recordTimestamp,
  isAIAssisted,
  getDiagnosisSource,
  guardrailPassed,
  parseOutcome,
} from "../utils/audit";

function formatTimestamp(ts) {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    return d.toISOString().replace("T", " ").slice(0, 19);
  } catch {
    return ts;
  }
}

export default function AuditTrailTable({ records, onSelectPayment }) {
  const rows = records || [];
  const [filter, setFilter] = useState("all");

  const counts = useMemo(() => {
    let ai = 0;
    let overrides = 0;
    let recovered = 0;

    for (const r of rows) {
      if (isAIAssisted(r)) ai += 1;
      if (r.stage === "stop_check" && !guardrailPassed(r)) overrides += 1;
      if (r.stage === "act" && parseOutcome(r) === "recovered") recovered += 1;
    }

    return {
      all: rows.length,
      ai,
      overrides,
      recovered,
    };
  }, [rows]);

  const filteredRows = useMemo(() => {
    if (filter === "ai") return rows.filter((r) => isAIAssisted(r));
    if (filter === "overrides") return rows.filter((r) => r.stage === "stop_check" && !guardrailPassed(r));
    if (filter === "recovered") return rows.filter((r) => r.stage === "act" && parseOutcome(r) === "recovered");
    return rows;
  }, [rows, filter]);

  return (
    <section className="audit-panel">
      <div className="audit-header-top">
        <div>
          <h2 className="chart-title" style={{ marginBottom: 2 }}>Immutable Multi-Agent Audit Trail</h2>
          <span className="audit-count">
            Showing {filteredRows.length} of {rows.length} entries · click any row to inspect full reasoning trace
          </span>
        </div>

        {/* Priority 1: Filter Chips */}
        <div className="audit-filter-chips" role="tablist" aria-label="Audit filter">
          <button
            type="button"
            className={`filter-chip ${filter === "all" ? "is-active" : ""}`}
            onClick={() => setFilter("all")}
          >
            All ({counts.all})
          </button>
          <button
            type="button"
            className={`filter-chip filter-chip-ai ${filter === "ai" ? "is-active" : ""}`}
            onClick={() => setFilter("ai")}
          >
            <Zap size={12} />
            ⚡ AI Diagnoses ({counts.ai})
          </button>
          <button
            type="button"
            className={`filter-chip filter-chip-override ${filter === "overrides" ? "is-active" : ""}`}
            onClick={() => setFilter("overrides")}
          >
            <ShieldAlert size={12} />
            🛡️ Overrides ({counts.overrides})
          </button>
          <button
            type="button"
            className={`filter-chip filter-chip-recovered ${filter === "recovered" ? "is-active" : ""}`}
            onClick={() => setFilter("recovered")}
          >
            <CheckCircle2 size={12} />
            💰 Recoveries ({counts.recovered})
          </button>
        </div>
      </div>

      {filteredRows.length === 0 ? (
        <div className="chart-empty">No audit entries match the selected filter.</div>
      ) : (
        <div className="audit-table-wrap">
          <table className="audit-table">
            <thead>
              <tr>
                <th>Payment ID</th>
                <th>Stage</th>
                <th>Reasoning & Forensic Insights</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((r, i) => {
                const meta = stageMeta(r.stage);
                const source = r.stage === "diagnose" ? getDiagnosisSource(r) : null;
                return (
                  <tr
                    key={`${r.payment_id}-${r.stage}-${i}`}
                    style={{ "--row-accent": meta.color }}
                    className="audit-row"
                    onClick={() => onSelectPayment?.(r.payment_id)}
                  >
                    <td className="mono font-medium">
                      <span className="payment-id-link">{r.payment_id}</span>
                    </td>
                    <td>
                      <span className="stage-badge" style={{ color: meta.color, borderColor: meta.color }}>
                        {meta.label}
                      </span>
                    </td>
                    <td className="reasoning-cell">
                      {source === "groq" && (
                        <span className="table-groq-pill">
                          <Zap size={10} />
                          <span>⚡ AI</span>
                        </span>
                      )}
                      {source === "cache" && (
                        <span className="table-cache-pill">
                          <Zap size={10} />
                          <span>⚡ Cache</span>
                        </span>
                      )}
                      {source === "deterministic_fallback" && (
                        <span className="table-fallback-pill">
                          <ShieldAlert size={10} />
                          <span>🛡 Fallback</span>
                        </span>
                      )}
                      <span>{r.reasoning}</span>
                    </td>
                    <td className="mono muted">{formatTimestamp(recordTimestamp(r))}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
