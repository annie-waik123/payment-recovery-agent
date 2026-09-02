import {
  isAIAssisted,
  getDiagnosisSource,
  parseForensicReasoning,
  parseBankHealth,
  computeAIDiagnosticsStats,
  computeAIContribution,
  STAGE_META,
  AGENT_DISPLAY_NAMES,
  parseRootCause,
  parseOutcome,
} from "./audit.js";

function runTests() {
  console.log("=== Testing Audit Utilities ===");

  // 1. STAGE_META check
  console.assert(STAGE_META.diagnose.label === "DIAGNOSE", "STAGE_META diagnose label");
  console.assert(AGENT_DISPLAY_NAMES.diagnose === "Diagnose Agent", "AGENT_DISPLAY_NAMES diagnose");
  console.assert(AGENT_DISPLAY_NAMES.decide === "Decision Agent", "AGENT_DISPLAY_NAMES decide");
  console.assert(AGENT_DISPLAY_NAMES.stop_check === "Guardrail Agent", "AGENT_DISPLAY_NAMES stop_check");
  console.assert(AGENT_DISPLAY_NAMES.act === "Executor Agent", "AGENT_DISPLAY_NAMES act");
  console.log("[OK] Stage metadata & display names verified");

  // 2. Rule-based diagnose entry
  const ruleEntry = {
    payment_id: "pay_1",
    stage: "diagnose",
    reasoning: "Root cause: insufficient_funds. error_code=BAD_REQUEST_ERROR error_reason=insufficient_funds matched insufficient-funds rules. [Source: deterministic_rules]",
    confidence: 1.0,
  };
  console.assert(isAIAssisted(ruleEntry) === false, "Rule entry is NOT AI assisted");
  console.assert(getDiagnosisSource(ruleEntry) === "deterministic_rules", "Source is deterministic_rules");
  console.assert(parseRootCause(ruleEntry) === "insufficient_funds", "Parse root cause from rule entry");
  console.assert(parseForensicReasoning(ruleEntry) === null, "No forensic reasoning in rule entry");
  console.assert(parseBankHealth(ruleEntry) === null, "No bank health in rule entry");
  console.log("[OK] Rule-based diagnosis parsing verified");

  // 3. AI Groq entry
  const groqEntry = {
    payment_id: "pay_2",
    stage: "diagnose",
    reasoning: "Root cause: network_timeout (confidence=0.82). ⚡ AI Forensic: Recurring latency spikes and dropped packets observed on gateway switch. [Bank Health: HDFC 45% SR - Degraded] [Source: groq]",
    confidence: 0.82,
  };
  console.assert(isAIAssisted(groqEntry) === true, "Groq entry is AI assisted");
  console.assert(getDiagnosisSource(groqEntry) === "groq", "Source is groq");
  console.assert(parseRootCause(groqEntry) === "network_timeout", "Parse root cause from Groq entry");
  console.assert(
    parseForensicReasoning(groqEntry) === "Recurring latency spikes and dropped packets observed on gateway switch.",
    "Groq forensic reasoning extracted"
  );
  console.assert(
    parseBankHealth(groqEntry) === "HDFC 45% SR - Degraded",
    "Bank health extracted correctly"
  );

  // 4. Cache entry
  const cacheEntry = {
    payment_id: "pay_3",
    stage: "diagnose",
    reasoning: "Root cause: network_timeout (confidence=0.82). ⚡ Cache Forensic: Recurring latency spikes and dropped packets observed on gateway switch. [Bank Health: HDFC 45% SR - Degraded] [Source: cache]",
    confidence: 0.82,
  };
  console.assert(isAIAssisted(cacheEntry) === true, "Cache entry is AI assisted");
  console.assert(getDiagnosisSource(cacheEntry) === "cache", "Source is cache");
  console.assert(
    parseForensicReasoning(cacheEntry) === "Recurring latency spikes and dropped packets observed on gateway switch.",
    "Cache forensic reasoning extracted"
  );

  // 5. Fallback entry
  const fallbackEntry = {
    payment_id: "pay_4",
    stage: "diagnose",
    reasoning: "Root cause: unknown. error_code=GATEWAY_ERROR error_reason=unknown_error did not match any deterministic recovery taxonomy rule. AI escalation also failed to produce a diagnosis. [Source: deterministic_fallback]",
    confidence: null,
  };
  console.assert(isAIAssisted(fallbackEntry) === false, "Fallback is not AI assisted");
  console.assert(getDiagnosisSource(fallbackEntry) === "deterministic_fallback", "Source is deterministic_fallback");

  console.log("[OK] Groq, Cache, and Fallback parsing verified");

  // 6. Batch stats computation
  const mockAudit = [
    ruleEntry,
    groqEntry,
    cacheEntry,
    fallbackEntry,
  ];

  const mockPayments = [
    { payment_id: "pay_1", amount: 100000, status: "recovered" },
    { payment_id: "pay_2", amount: 250000, status: "recovered" },
    { payment_id: "pay_3", amount: 150000, status: "recovered" },
    { payment_id: "pay_4", amount: 150000, status: "failed" },
  ];

  const mockMetrics = {
    total_payments: 4,
    recovered_count: 3,
    unrecoverable_count: 1,
    recovery_rate: 0.75,
    revenue_at_risk_paise: 650000,
    revenue_recovered_paise: 500000,
  };

  const aiStats = computeAIDiagnosticsStats(mockAudit, mockMetrics, mockPayments);
  console.assert(aiStats.ruleDiagnosesCount === 2, "ruleDiagnosesCount == 2");
  console.assert(aiStats.aiDiagnosesCount === 2, "aiDiagnosesCount == 2");

  console.assert(aiStats.groqCount === 1, "groqCount == 1");
  console.assert(aiStats.cacheHitCount === 1, "cacheHitCount == 1");
  console.assert(aiStats.fallbackCount === 1, "fallbackCount == 1");
  console.log("[OK] AI Diagnostics Stats computation verified:", aiStats);

  console.log("\n[SUCCESS] All audit utility unit tests passed successfully!");
}

runTests();
