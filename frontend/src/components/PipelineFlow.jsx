import { Fragment } from "react";
import { AlertTriangle, ScanSearch, GitBranch, ShieldCheck, Zap, CheckCircle2 } from "lucide-react";
import { STAGE_ORDER, stageMeta } from "../utils/audit";

const STAGE_ICONS = {
  diagnose: ScanSearch,
  decide: GitBranch,
  stop_check: ShieldCheck,
  act: Zap,
};

function Arrow() {
  return (
    <div className="pipeline-arrow-track" aria-hidden="true">
      <div className="pipeline-arrow-flow" />
    </div>
  );
}

/**
 * Failed Payment -> Diagnose -> Decide -> Guardrail -> Executor -> Outcome.
 * Endpoint nodes (input/outcome) are visual bookends, not audit stages —
 * they read straight from /metrics so the pipeline tells the whole story
 * even before drilling into individual agents.
 */
export default function PipelineFlow({ stageCounts, metrics, executorStats }) {
  const total = metrics?.total_payments ?? 0;
  const recovered = metrics?.recovered_count ?? 0;
  const unrecoverable = metrics?.unrecoverable_count ?? 0;
  // "Pending" was misleading — most non-recovered payments are deliberate
  // guardrail holds, not retries stuck mid-flight. Split them using the
  // audit-derived executor outcomes instead.
  const held = executorStats?.held ?? 0;
  const stillFailing = executorStats?.still_failing ?? 0;

  return (
    <section className="chart-panel">
      <h2 className="chart-title">Agent Pipeline</h2>
      <div className="pipeline-flow">
        <div className="pipeline-node pipeline-endpoint">
          <AlertTriangle size={18} className="pipeline-icon" style={{ color: "var(--c-unrecoverable)" }} />
          <div className="pipeline-agent">Failed Payment</div>
          <div className="pipeline-count mono">{total}</div>
        </div>

        {STAGE_ORDER.map((stage) => {
          const meta = stageMeta(stage);
          const count = stageCounts?.[stage] ?? 0;
          const Icon = STAGE_ICONS[stage];
          const active = count > 0;
          return (
            <Fragment key={stage}>
              <Arrow />
              <div className="pipeline-node" style={{ "--node-accent": meta.color }}>
                {Icon && <Icon size={18} className="pipeline-icon" style={{ color: meta.color }} />}
                <div className="pipeline-agent">{meta.agent}</div>
                <div className="pipeline-stage-label" style={{ color: meta.color }}>
                  {meta.label}
                </div>
                <div className="pipeline-count mono">{count}</div>
                <div className={`pipeline-status ${active ? "is-active" : "is-idle"}`}>
                  <span
                    className="pipeline-status-dot"
                    style={{ background: active ? meta.color : "var(--text-faint)" }}
                  />
                  {active ? "active" : "idle"}
                </div>
              </div>
            </Fragment>
          );
        })}

        <Arrow />
        <div className="pipeline-node pipeline-endpoint">
          <CheckCircle2 size={18} className="pipeline-icon" style={{ color: "var(--c-recovered)" }} />
          <div className="pipeline-agent">Outcome</div>
          <div className="pipeline-outcome-breakdown">
            <span style={{ color: "var(--c-recovered)" }}>{recovered} recovered</span>
            {stillFailing > 0 && <span style={{ color: "var(--c-warning)" }}>{stillFailing} retried, still failing</span>}
            {held > 0 && <span className="muted">{held} held by guardrails</span>}
            {unrecoverable > 0 && <span style={{ color: "var(--c-unrecoverable)" }}>{unrecoverable} unrecoverable</span>}
          </div>
        </div>
      </div>
    </section>
  );
}
