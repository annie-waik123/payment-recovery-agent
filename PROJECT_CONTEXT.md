# PROJECT_CONTEXT.md

## Project

RecoveryMind AI

Multi-agent payment recovery platform built for the Razorpay AI Buildathon.

**Goal:** Increase payment Success Rate (SR) and recover merchant revenue lost due to failed transactions.

---

## Current Status

- **Backend:** ✅ Complete
- **Frontend:** ✅ Complete
- **Dashboard:** ✅ Complete & Reconciled
- **Audit Trail:** ✅ Immutable & Filterable
- **Pipeline Visualization:** ✅ Working
- **AI Diagnosis Engine:** ✅ Groq LPU + In-Memory Fingerprint Cache

---

## Core Principles

### Principle 1: Rules Decide Money
AI never decides money movement or interventions. Groq strictly diagnoses the root cause of ambiguous failures. All financial actions remain deterministic and auditable.

### Principle 2: Rules First, AI Second
Known failures (~85%) are resolved by deterministic rules at 0ms latency and $0 compute cost. Only ambiguous residual failures are escalated to the AI layer.

### Principle 3: Guardrails Hold Final Authority
The Guardrail Agent enforces hard limits (spend caps, retry counts, cooldown windows) and has the unilateral authority to override or block any recovery action.

---

## Diagnostic Hierarchy

1. **Deterministic Rules:** Checked first at 0ms. Never cached.
2. **Diagnosis Cache:** In-memory fingerprint matching on `(error_code, error_reason, method, bank_name, bank_status)`.
3. **Primary AI (Groq):** `qwen/qwen3.8-27b` via Groq's low-latency LPU endpoint.
4. **Deterministic Fallback:** Safe degradation to `RootCause.UNKNOWN` and `HOLD` quarantine.

---

## Source Attribution in AuditLog

- `source = groq` (Marker: `⚡ AI Forensic:`)
- `source = cache` (Marker: `⚡ Cache Forensic:`)
- `source = deterministic_fallback` (Quarantine)
- `source = deterministic_rules` (Rule-based)

---

## Multi-Agent Pipeline

1. **Diagnose Agent:** Identifies root cause using Rules $\rightarrow$ Cache $\rightarrow$ Groq $\rightarrow$ Fallback.
2. **Decision Agent:** Maps root cause to optimal intervention (`retry_now`, `retry_later`, `suggest_alt_method`, `hold`).
3. **Guardrail Agent:** Validates financial safety constraints and spend caps.
4. **Executor Agent:** Executes approved interventions and records outcomes.

---

## Buildathon Positioning

RecoveryMind AI is not an autonomous payment executor. It is an intelligent decisioning and diagnostic layer that increases payment Success Rates while protecting merchants with strict financial guardrails.