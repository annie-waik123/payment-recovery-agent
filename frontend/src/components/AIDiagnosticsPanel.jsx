import { Zap, BrainCircuit, Activity, CheckCircle2, TrendingUp, Search, Database, ShieldCheck } from "lucide-react";
import { formatPaise, computeAIDiagnosticsStats, isAIAssisted } from "../utils/audit";

function AiCard({ label, value, sub, accent, icon: Icon, badge }) {
  return (
    <div className="stat-card ai-stat-card" style={{ "--card-accent": accent }}>
      <div className="ai-card-header">
        <div className="stat-label">{label}</div>
        {Icon && <Icon size={16} className="ai-card-icon" style={{ color: accent }} />}
      </div>
      <div className="stat-value stat-value-mono">{value ?? "—"}</div>
      {badge && <div className="ai-card-badge">{badge}</div>}
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

export default function AIDiagnosticsPanel({ records, metrics, payments, onSelectPayment }) {
  const stats = computeAIDiagnosticsStats(records, metrics, payments);

  const {
    ruleDiagnosesCount = 0,
    aiDiagnosesCount = 0,
    groqCount = 0,
    cacheHitCount = 0,
    avgConfidence = null,
    escalationRate = 0,
    recoveredCount = 0,
    recoveredRevenuePaise = 0,
    recoveryRate = 0,
    totalPayments = 0,
  } = stats;

  // Find the first payment with an AI-assisted diagnosis for 1-click inspection
  const sampleAiPaymentId = records?.find((r) => isAIAssisted(r))?.payment_id;

  function handleInspectSample() {
    if (sampleAiPaymentId && onSelectPayment) {
      onSelectPayment(sampleAiPaymentId);
    }
  }

  const hasPositiveRevenue = recoveredRevenuePaise > 0;
  const hasConfidenceScore = avgConfidence !== null && avgConfidence > 0;

  return (
    <section className="ai-diagnostics-section">
      <div className="ai-section-header">
        <div>
          <div className="section-label">AI Diagnostic Intelligence (Groq + Cache)</div>
          <div className="ai-tools-row">
            <span className="ai-tool-pill">
              <Database size={11} />
              <span>Integrated Tools: 🏦 Mock Bank Health Telemetry</span>
            </span>
            <span className="ai-tool-pill" style={{ borderColor: "#F59E0B" }}>
              <Zap size={11} style={{ color: "#F59E0B" }} />
              <span>Engine: ⚡ Groq AI</span>
            </span>
            <span className="ai-tool-pill" style={{ borderColor: "#10B981" }}>
              <Zap size={11} style={{ color: "#34D399" }} />
              <span>Cache: ⚡ Fingerprint Hits ({cacheHitCount})</span>
            </span>
          </div>
        </div>

        <div className="ai-header-actions">
          {sampleAiPaymentId ? (
            <button
              type="button"
              className="btn-inspect-ai"
              onClick={handleInspectSample}
              title="Click to open reasoning trace of an AI-diagnosed failure"
            >
              <Search size={13} />
              <span>Inspect Sample AI Diagnosis ({sampleAiPaymentId})</span>
            </button>
          ) : (
            <div className="ai-badge-header">
              <Zap size={13} style={{ color: "#F59E0B" }} />
              <span>Rules First · AI Second</span>
            </div>
          )}
        </div>
      </div>

      <div className="stats-grid ai-stats-grid">
        {/* Card 1: AI vs Rules Breakdown */}
        <div className="stat-card ai-stat-card ai-vs-rules-card" style={{ "--card-accent": "var(--c-decide)" }}>
          <div className="ai-card-header">
            <div className="stat-label">AI vs Rules Breakdown</div>
            <BrainCircuit size={16} style={{ color: "var(--c-decide)" }} />
          </div>
          <div className="ai-vs-rules-values">
            <div className="ai-vs-rules-row">
              <span className="muted">Rule Diagnoses</span>
              <span className="mono bold">{ruleDiagnosesCount}</span>
            </div>
            <div className="ai-vs-rules-row">
              <span className="muted">Ambiguous Investigated</span>
              <span className="mono bold" style={{ color: "var(--c-decide)" }}>{aiDiagnosesCount}</span>
            </div>
          </div>
          <div className="ai-vs-rules-footer">
            <span className="ai-sub-tag">AI only handled ambiguity</span>
          </div>
        </div>

        {/* Card 2: AI Diagnostic Coverage & Cache Efficiency */}
        <AiCard
          label="AI Escalation Coverage"
          value={`${escalationRate.toFixed(1)}%`}
          sub={
            cacheHitCount > 0
              ? `${aiDiagnosesCount} investigated (${cacheHitCount} cache hit${cacheHitCount === 1 ? "" : "s"})`
              : `${aiDiagnosesCount} of ${totalPayments} failures escalated to AI`
          }
          accent="var(--c-info)"
          icon={Activity}
        />

        {/* Card 3: Forensic Confidence */}
        <AiCard
          label="Forensic Confidence"
          value={hasConfidenceScore ? `${(avgConfidence * 100).toFixed(1)}%` : "Active"}
          sub={
            hasConfidenceScore
              ? `AI certainty (Groq: ${groqCount} | Cache: ${cacheHitCount})`
              : "Safe fallback reasoning applied"
          }
          accent="#818CF8"
          icon={Zap}
        />

        {/* Card 4: Forensic Diagnoses Generated */}
        <AiCard
          label="Forensic Diagnoses"
          value={aiDiagnosesCount}
          sub={
            recoveredCount > 0
              ? `${recoveredCount} recovered (${recoveryRate.toFixed(0)}% recovery rate)`
              : "Forensic root-cause analyses produced"
          }
          accent="var(--c-recovered)"
          icon={CheckCircle2}
        />

        {/* Card 5: AI Revenue Impact or Safe Containment */}
        {hasPositiveRevenue ? (
          <AiCard
            label="AI Recovery Revenue"
            value={formatPaise(recoveredRevenuePaise)}
            sub="Revenue recovered via AI pipeline"
            accent="var(--c-primary)"
            icon={TrendingUp}
          />
        ) : (
          <AiCard
            label="Safe Risk Containment"
            value="100% Protected"
            sub="Ambiguous failures held by guardrails"
            accent="var(--c-primary)"
            icon={ShieldCheck}
          />
        )}
      </div>
    </section>
  );
}
