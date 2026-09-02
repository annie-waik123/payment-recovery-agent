import { useEffect } from "react";
import { Zap, ShieldAlert, Activity } from "lucide-react";
import {
  STAGE_ORDER,
  stageMeta,
  AGENT_DISPLAY_NAMES,
  parseRootCause,
  parseInterventionFromDecide,
  parseInterventionFromAct,
  parseOutcome,
  guardrailPassed,
  isAIAssisted,
  getDiagnosisSource,
  parseForensicReasoning,
  parseBankHealth,
} from "../utils/audit";

function Field({ label, children, fullWidth = false }) {
  return (
    <div className={`drawer-field ${fullWidth ? "drawer-field-full" : ""}`}>
      <div className="drawer-field-label">{label}</div>
      <div className="drawer-field-value">{children}</div>
    </div>
  );
}

export default function PaymentDetailDrawer({ paymentId, entries, onClose }) {
  useEffect(() => {
    function handleKey(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  if (!paymentId) return null;

  const diagnose = entries?.diagnose;
  const decide = entries?.decide;
  const stopCheck = entries?.stop_check;
  const act = entries?.act;

  const aiAssisted = isAIAssisted(diagnose);
  const source = getDiagnosisSource(diagnose);
  const rootCause = parseRootCause(diagnose);
  const confidence = diagnose?.confidence;
  const forensicReasoning = parseForensicReasoning(diagnose);
  const bankHealth = parseBankHealth(diagnose);
  const intervention = parseInterventionFromDecide(decide) || parseInterventionFromAct(act);
  const passed = guardrailPassed(stopCheck);
  const outcome = parseOutcome(act);

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-top">
          <div>
            <div className="drawer-eyebrow">PAYMENT DETAIL & REASONING TRACE</div>
            <div className="drawer-payment-id-row">
              <span className="drawer-payment-id mono">{paymentId}</span>
              {source === "groq" && (
                <span className="groq-pill-badge">
                  <Zap size={11} />
                  <span>⚡ AI Diagnosis</span>
                </span>
              )}
              {source === "cache" && (
                <span className="cache-pill-badge">
                  <Zap size={11} />
                  <span>⚡ Cache Diagnosis</span>
                </span>
              )}
              {source === "deterministic_fallback" && (
                <span className="fallback-pill-badge">
                  <ShieldAlert size={11} />
                  <span>🛡 Fallback</span>
                </span>
              )}
              {source === "deterministic_rules" && (
                <span className="rules-pill-badge">
                  <span>📋 Rules</span>
                </span>
              )}
            </div>
          </div>
          <button className="drawer-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        {/* AI Forensic Highlight Callout */}
        {aiAssisted && (
          <div className="drawer-ai-callout">
            <div className="drawer-ai-callout-head">
              <Zap size={14} style={{ color: "#F59E0B" }} />
              <span className="drawer-ai-callout-title">
                {source === "cache" ? "⚡ Cached AI Diagnosis" : "⚡ AI Forensic Diagnosis"}
              </span>
              <span className="drawer-ai-callout-tag">
                {source === "cache" ? "In-Memory Fingerprint Hit" : "Fallback Escalation"}
              </span>
            </div>
            {forensicReasoning && (
              <div className="drawer-ai-callout-text">
                "{forensicReasoning}"
              </div>
            )}
            {bankHealth && (
              <div className="drawer-bank-health-tag">
                <Activity size={12} />
                <span>Bank Telemetry: {bankHealth}</span>
              </div>
            )}
          </div>
        )}

        <div className="drawer-summary">
          <Field label="Root Cause">
            <span className="mono bold">{rootCause ? rootCause.replace(/_/g, " ") : "—"}</span>
          </Field>
          <Field label="Diagnosis Method">
            {aiAssisted ? (
              <span className="text-ai-highlight">
                {source === "cache" ? "AI Cache" : "AI Inferred"} ({confidence ? `${(confidence * 100).toFixed(0)}%` : "—"})
              </span>
            ) : source === "deterministic_fallback" ? (
              <span className="muted">Quarantine Fallback</span>
            ) : (
              <span className="text-rule-highlight">Rule-Based (100%)</span>
            )}
          </Field>
          <Field label="Policy Intervention">
            <span className="mono">{intervention ? intervention.replace(/_/g, " ") : "—"}</span>
          </Field>
          <Field label="Guardrail Safety">
            {passed === null ? (
              "—"
            ) : (
              <span className={passed ? "pill-pass" : "pill-block"}>
                {passed ? "Passed" : "Blocked / Modified"}
              </span>
            )}
          </Field>
          <Field label="Final Outcome" fullWidth>
            {outcome ? (
              <span className={`pill-outcome pill-outcome-${outcome}`}>
                {outcome.replace(/_/g, " ").toUpperCase()}
              </span>
            ) : (
              "—"
            )}
          </Field>
        </div>

        <div className="drawer-divider" />

        <div className="drawer-eyebrow" style={{ marginBottom: 12 }}>
          MULTI-AGENT REASONING TRACE
        </div>
        <div className="drawer-stage-list">
          {STAGE_ORDER.map((stage) => {
            const entry = entries?.[stage];
            const meta = stageMeta(stage);
            const agentName = AGENT_DISPLAY_NAMES[stage] || meta.agent;
            return (
              <div className="drawer-stage-entry" key={stage} style={{ "--row-accent": meta.color }}>
                <div className="drawer-stage-head">
                  <span className="stage-badge" style={{ color: meta.color, borderColor: meta.color }}>
                    {meta.label}
                  </span>
                  <span className="drawer-stage-agent-name">{agentName}</span>
                </div>
                <div className="drawer-stage-reasoning">
                  {entry ? (
                    <div className="reasoning-text-block">{entry.reasoning}</div>
                  ) : (
                    <span className="muted">Not yet reached</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </aside>
    </div>
  );
}
