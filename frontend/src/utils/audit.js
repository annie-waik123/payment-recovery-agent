// Single source of truth for stage -> agent mapping and colors, so the
// pipeline visualization, audit table, and payment drawer never drift.
export const STAGE_ORDER = ["diagnose", "decide", "stop_check", "act"];

export const STAGE_META = {
  diagnose: { label: "DIAGNOSE", color: "#60A5FA", agent: "Classifier" },
  decide: { label: "DECIDE", color: "#C084FC", agent: "Policy Engine" },
  stop_check: { label: "STOP CHECK", color: "#FBBF24", agent: "Guardrails" },
  act: { label: "ACT", color: "#34D399", agent: "Executor" },
};

export function stageMeta(stage) {
  return STAGE_META[stage] || { label: stage?.toUpperCase() || "—", color: "#8B93A7", agent: stage };
}

/**
 * Some backend revisions send `timestamp`, others `created_at` — accept
 * either so a field-name mismatch degrades to "—" instead of silently
 * breaking every timestamp-dependent view (audit table, execution timeline).
 */
export function recordTimestamp(record) {
  return record?.timestamp ?? record?.created_at ?? null;
}

/** { payment_id: { diagnose, decide, stop_check, act } } — latest entry per stage wins. */
export function groupAuditByPayment(records) {
  const byPayment = {};
  for (const r of records || []) {
    if (!byPayment[r.payment_id]) byPayment[r.payment_id] = {};
    byPayment[r.payment_id][r.stage] = r;
  }
  return byPayment;
}

/** Count of audit entries per pipeline stage — drives the pipeline visualization. */
export function computeStageCounts(records) {
  const counts = { diagnose: 0, decide: 0, stop_check: 0, act: 0 };
  for (const r of records || []) {
    if (counts[r.stage] !== undefined) counts[r.stage] += 1;
  }
  return counts;
}

/** Per-stage first/last timestamp + count, for the execution timeline card. */
export function computeStageTimeline(records) {
  const stats = {};
  for (const r of records || []) {
    if (!STAGE_ORDER.includes(r.stage)) continue;
    const t = new Date(recordTimestamp(r)).getTime();
    if (Number.isNaN(t)) continue;
    if (!stats[r.stage]) stats[r.stage] = { stage: r.stage, start: t, end: t, count: 0 };
    stats[r.stage].start = Math.min(stats[r.stage].start, t);
    stats[r.stage].end = Math.max(stats[r.stage].end, t);
    stats[r.stage].count += 1;
  }
  const entries = STAGE_ORDER.map((s) => stats[s]).filter(Boolean);
  if (entries.length === 0) return { entries: [], rangeStart: 0, rangeEnd: 1 };
  const rangeStart = Math.min(...entries.map((e) => e.start));
  const rawEnd = Math.max(...entries.map((e) => e.end));
  return { entries, rangeStart, rangeEnd: rawEnd === rangeStart ? rangeStart + 1 : rawEnd };
}

export function parseRootCause(diagnoseEntry) {
  const m = diagnoseEntry?.reasoning?.match(/Root cause:\s*([a-zA-Z_]+)/i);
  return m ? m[1] : null;
}

export function parseInterventionFromDecide(decideEntry) {
  const m = decideEntry?.reasoning?.match(/Chosen intervention:\s*([a-zA-Z_]+)/i);
  return m ? m[1] : null;
}

/**
 * Decision Agent's own output, counted from `decide`-stage audit entries —
 * NOT from metrics.intervention_breakdown. That breakdown reflects the
 * FINAL intervention type after guardrails.py may have overridden it (it
 * mutates Intervention.type in place), so using it here would silently
 * attribute Guardrail Agent's overrides to the Decision Agent. The decide
 * audit row is written before guardrails runs, so it still holds the
 * original proposed intervention.
 */
export function computeDecisionStats(records) {
  const counts = {};
  for (const r of records || []) {
    if (r.stage !== "decide") continue;
    const intervention = parseInterventionFromDecide(r);
    if (!intervention) continue;
    counts[intervention] = (counts[intervention] || 0) + 1;
  }
  return counts;
}

/**
 * Real executor.py reasoning format:
 *   "Executed intervention retry_now. Result: recovered. New status: recovered. Retry count: 1."
 * Parses all three fields in one match. `newStatus` is more reliable than
 * `outcome` for distinguishing "still retrying" from "unrecoverable" —
 * executor.py writes outcome="still_failing" for BOTH cases (see its
 * UNRECOVERABLE branch), so outcome alone can't tell them apart.
 */
export function parseActEntry(actEntry) {
  const m = actEntry?.reasoning?.match(
    /^Executed intervention\s+([a-zA-Z_]+)\.\s*Result:\s*([a-zA-Z_]+)\.\s*New status:\s*([a-zA-Z_]+)\./i
  );
  if (!m) return null;
  return { intervention: m[1], outcome: m[2], newStatus: m[3] };
}

export function parseInterventionFromAct(actEntry) {
  return parseActEntry(actEntry)?.intervention ?? null;
}

/** Normalized to: "recovered" | "unrecoverable" | "held" | "still_failing" | null. */
export function parseOutcome(actEntry) {
  const parsed = parseActEntry(actEntry);
  if (!parsed) return null;
  if (parsed.newStatus === "unrecoverable") return "unrecoverable";
  if (parsed.outcome === "recovered") return "recovered";
  if (parsed.outcome === "held") return "held";
  return "still_failing";
}

export function guardrailPassed(stopCheckEntry) {
  if (!stopCheckEntry?.reasoning) return null;
  return /^stop check passed/i.test(stopCheckEntry.reasoning.trim());
}

/**
 * Average success rate of money-moving retries (retry_now / retry_later),
 * derived from "act" stage entries — no backend change needed since the
 * intervention type and outcome are both embedded in the existing
 * reasoning string.
 */
export function computeAvgRetrySuccess(records) {
  let attempts = 0;
  let successes = 0;
  for (const r of records || []) {
    if (r.stage !== "act") continue;
    const intervention = parseInterventionFromAct(r);
    if (intervention !== "retry_now" && intervention !== "retry_later") continue;
    attempts += 1;
    if (parseOutcome(r) === "recovered") successes += 1;
  }
  return attempts > 0 ? successes / attempts : null;
}

/**
 * Guardrail Agent's own scorecard, derived entirely from stop_check audit
 * entries already in hand — no new endpoint. "Blocked" reasoning always
 * starts with "Stop check blocked." (see guardrails.py), so we also parse
 * out *why* it blocked (max_retries / low_confidence / cooldown / caps)
 * for a breakdown, matching the block_reason categories the backend uses.
 */
export function computeGuardrailStats(records) {
  const stopChecks = (records || []).filter((r) => r.stage === "stop_check");
  const total = stopChecks.length;
  let approved = 0;
  let overridden = 0;
  const overrideReasons = {};

  for (const r of stopChecks) {
    const reasoning = r.reasoning || "";
    if (/^stop check passed/i.test(reasoning.trim())) {
      approved += 1;
      continue;
    }
    overridden += 1;
    let reason = "other";
    if (/max_retries|>=\s*MAX_RETRIES/i.test(reasoning)) reason = "max_retries";
    else if (/low.?confidence|confidence=/i.test(reasoning)) reason = "low_confidence";
    else if (/cooldown/i.test(reasoning)) reason = "cooldown";
    else if (/spend cap|batch_spend_cap/i.test(reasoning)) reason = "spend_cap";
    else if (/action cap|batch_action_cap/i.test(reasoning)) reason = "action_cap";
    overrideReasons[reason] = (overrideReasons[reason] || 0) + 1;
  }

  return {
    total,
    approved,
    overridden,
    overridePct: total > 0 ? (overridden / total) * 100 : null,
    overrideReasons,
  };
}

/** Highest-count entry in a breakdown object, e.g. metrics.root_cause_breakdown. */
export function getTopEntry(breakdown) {
  const entries = Object.entries(breakdown || {});
  if (entries.length === 0) return null;
  return entries.reduce((top, cur) => (cur[1] > top[1] ? cur : top));
}

/** Executor Agent's own scorecard — outcome counts parsed from act entries. */
export function computeExecutorStats(records) {
  const stats = { recovered: 0, still_failing: 0, unrecoverable: 0, held: 0, other: 0 };
  for (const r of records || []) {
    if (r.stage !== "act") continue;
    const outcome = parseOutcome(r);
    if (outcome && stats[outcome] !== undefined) stats[outcome] += 1;
    else stats.other += 1;
  }
  return stats;
}

/** { intervention: { attempts, successes } } across all act entries. */
export function computeInterventionSuccess(records) {
  const map = {};
  for (const r of records || []) {
    if (r.stage !== "act") continue;
    const intervention = parseInterventionFromAct(r);
    if (!intervention) continue;
    if (!map[intervention]) map[intervention] = { attempts: 0, successes: 0 };
    map[intervention].attempts += 1;
    if (parseOutcome(r) === "recovered") map[intervention].successes += 1;
  }
  return map;
}

/** The intervention type with the most recovered outcomes, for the batch summary sentence. */
export function mostSuccessfulIntervention(records) {
  const map = computeInterventionSuccess(records);
  const entries = Object.entries(map);
  if (entries.length === 0) return null;
  const [name, stats] = entries.reduce((top, cur) => (cur[1].successes > top[1].successes ? cur : top));
  return stats.successes > 0 ? { name, ...stats } : null;
}

export function formatPaise(paise) {
  if (paise === null || paise === undefined) return null;
  return `₹${Math.round(paise / 100).toLocaleString("en-IN")}`;
}

export const AGENT_DISPLAY_NAMES = {
  diagnose: "Diagnose Agent",
  decide: "Decision Agent",
  stop_check: "Guardrail Agent",
  act: "Executor Agent",
};

/** Identifies if a diagnose entry was generated by AI escalation (Groq or Cache). */
export function isAIAssisted(diagnoseEntry) {
  if (!diagnoseEntry) return false;
  const src = getDiagnosisSource(diagnoseEntry);
  if (src === "groq" || src === "cache") return true;
  const reasoning = diagnoseEntry.reasoning || "";
  if (reasoning.includes("AI Forensic") || reasoning.includes("Cache Forensic") || reasoning.includes("groq") || reasoning.includes("Groq")) {
    return true;
  }
  if (diagnoseEntry.confidence !== null && diagnoseEntry.confidence !== undefined && diagnoseEntry.confidence < 1.0) {
    return true;
  }
  return false;
}

/** Extracts the diagnosis source: 'groq' | 'cache' | 'deterministic_fallback' | 'deterministic_rules'. */
export function getDiagnosisSource(diagnoseEntry) {
  if (!diagnoseEntry?.reasoning) return "deterministic_rules";
  const reasoning = diagnoseEntry.reasoning;
  const match = reasoning.match(/\[Source:\s*([a-zA-Z_]+)\]/i);
  if (match) return match[1].toLowerCase();
  if (reasoning.includes("⚡ Cache") || reasoning.includes("Cache Forensic")) return "cache";
  if (reasoning.includes("⚡ AI Forensic") || reasoning.includes("groq") || reasoning.includes("Groq") || reasoning.includes("AI Forensic")) return "groq";
  if (reasoning.includes("deterministic_fallback") || (reasoning.includes("Root cause: unknown") && reasoning.includes("failed"))) {
    return "deterministic_fallback";
  }
  return "deterministic_rules";
}

/** Extracts the forensic reasoning string from an AI diagnose audit entry. */
export function parseForensicReasoning(diagnoseEntry) {
  if (!diagnoseEntry?.reasoning) return null;
  const m = diagnoseEntry.reasoning.match(/⚡?\s*(?:AI\s+|Cache\s+)?Forensic:\s*([^\[]+?)(?=\s*\[(?:Bank Health|Source):|$)/i);
  if (m) return m[1].trim();
  const fallback = diagnoseEntry.reasoning.match(/Forensic:\s*([^\[]+)/i);
  return fallback ? fallback[1].trim() : null;
}

/** Extracts the bank health string from a diagnose audit entry if present. */
export function parseBankHealth(diagnoseEntry) {
  if (!diagnoseEntry?.reasoning) return null;
  const m = diagnoseEntry.reasoning.match(/\[Bank Health:\s*([^\]]+)\]/i);
  if (m) return m[1].trim();
  const fallback = diagnoseEntry.reasoning.match(/Bank Health:\s*([^;\.\n]+)/i);
  return fallback ? fallback[1].trim() : null;
}

/** Computes comprehensive AI diagnostic statistics across audit records and payments. */
export function computeAIDiagnosticsStats(records, metrics, payments = []) {
  const grouped = groupAuditByPayment(records);
  const paymentMap = {};
  for (const p of payments || []) {
    paymentMap[p.payment_id] = p;
  }

  let ruleDiagnosesCount = 0;
  let aiDiagnosesCount = 0;
  let groqCount = 0;
  let cacheHitCount = 0;
  let fallbackCount = 0;
  let totalAiConfidence = 0;
  let recoveredCount = 0;
  let recoveredRevenuePaise = 0;
  let aiRevenueAtRiskPaise = 0;

  const paymentIds = Object.keys(grouped);
  const totalPayments = metrics?.total_payments || paymentIds.length || payments.length;

  for (const pid of paymentIds) {
    const diag = grouped[pid]?.diagnose;
    const paymentObj = paymentMap[pid];
    const act = grouped[pid]?.act;
    const isRecovered = parseOutcome(act) === "recovered" || paymentObj?.status === "recovered";
    const amount = paymentObj?.amount || 0;
    const source = getDiagnosisSource(diag);

    if (source === "groq") groqCount += 1;
    else if (source === "cache") cacheHitCount += 1;
    else if (source === "deterministic_fallback") fallbackCount += 1;

    if (isAIAssisted(diag)) {
      aiDiagnosesCount += 1;
      if (diag.confidence !== null && diag.confidence !== undefined) {
        totalAiConfidence += diag.confidence;
      }
      aiRevenueAtRiskPaise += amount;
      if (isRecovered) {
        recoveredCount += 1;
        recoveredRevenuePaise += amount;
      }
    } else if (diag) {
      ruleDiagnosesCount += 1;
    }
  }

  if (ruleDiagnosesCount + aiDiagnosesCount < totalPayments && totalPayments > 0) {
    ruleDiagnosesCount = Math.max(0, totalPayments - aiDiagnosesCount);
  }

  const avgConfidence = aiDiagnosesCount > 0 ? totalAiConfidence / aiDiagnosesCount : null;
  const escalationRate = totalPayments > 0 ? (aiDiagnosesCount / totalPayments) * 100 : 0;
  const recoveryRate = aiDiagnosesCount > 0 ? (recoveredCount / aiDiagnosesCount) * 100 : 0;

  return {
    ruleDiagnosesCount,
    aiDiagnosesCount,
    groqCount,
    cacheHitCount,
    fallbackCount,
    avgConfidence,
    escalationRate,
    recoveredCount,
    recoveredRevenuePaise,
    aiRevenueAtRiskPaise,
    recoveryRate,
    totalPayments,
  };
}

/** Computes AI's contribution relative to overall batch recovery metrics. */
export function computeAIContribution(records, payments, metrics) {
  const stats = computeAIDiagnosticsStats(records, metrics, payments);
  const totalRecovered = metrics?.recovered_count ?? 0;
  const totalRecoveredRevenue = metrics?.revenue_recovered_paise ?? 0;

  const aiRecoveryShare = totalRecovered > 0 ? (stats.recoveredCount / totalRecovered) * 100 : 0;
  const aiRevenueShare = totalRecoveredRevenue > 0 ? (stats.recoveredRevenuePaise / totalRecoveredRevenue) * 100 : 0;

  return {
    ...stats,
    aiRecoveryShare,
    aiRevenueShare,
  };
}



