# System Architecture: RecoveryMind AI

## Overview

RecoveryMind AI is an explainable, multi-agent payment recovery intelligence layer designed for high-throughput Indian fintech environments.

The architecture strictly follows one foundational principle:

> **"Rules Decide Money. AI Diagnoses Ambiguity. Guardrails Hold Final Authority."**

---

## High-Level Pipeline Architecture

```text
[ Failed Payment Webhook ]
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ 1. DIAGNOSE AGENT                                      │
│    ├── 1. Deterministic Taxonomy Rules (0ms, 85% vol)  │
│    ├── 2. In-Memory Diagnosis Cache (0ms on hits)      │
│    ├── 3. Groq AI Escalation (LPU inference <500ms)    │
│    └── 4. Deterministic Fallback (Quarantine Hold)     │
└──────────────────────────┬─────────────────────────────┘
                           │ RootCause + Confidence + Forensic Reasoning
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. DECISION AGENT (Deterministic Policy Engine)        │
│    └── Maps Root Cause ──► Policy Intervention         │
│        (retry_now, retry_later, suggest_alt_method,    │
│         hold)                                          │
└──────────────────────────┬─────────────────────────────┘
                           │ Proposed Intervention
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. GUARDRAIL AGENT (Safety & Financial Control)        │
│    ├── Spend Cap Verification (₹20,000 max / batch)    │
│    ├── Retry Limit Check (max 3 retries / payment)     │
│    ├── Cooldown Window Enforcement (300s window)       │
│    └── Override Authority: Approve / Block / Modify    │
└──────────────────────────┬─────────────────────────────┘
                           │ Approved Intervention
                           ▼
┌────────────────────────────────────────────────────────┐
│ 4. EXECUTOR AGENT (Gateway & Outcome Simulation)       │
│    └── Executes Action ──► Emits Final Status          │
│        (recovered, held, still_failing, unrecoverable) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 5. IMMUTABLE AUDIT TRAIL & RECONCILIATION ENGINE       │
│    └── Records full multi-agent reasoning trace        │
│        and live financial impact across all metrics    │
└────────────────────────────────────────────────────────┘
```

---

## 1. Diagnose Agent: 4-Layer Diagnostic Hierarchy

```text
Failed Payment
      │
      ▼
1. Deterministic Rules (85% known patterns, 0ms, $0)
      │ (residual unknown only)
      ▼
2. Diagnosis Cache (in-memory fingerprint match)
      │ (cache miss)
      ▼
3. Primary AI: Groq (qwen/qwen3.8-27b on OpenAI-compatible endpoint)
      │ (if AI provider unavailable)
      ▼
4. Deterministic Fallback & Guardrails (RootCause.UNKNOWN + Quarantine Hold)
```

### Stage 1: Deterministic Rules
- 85% of volume (`insufficient_funds`, `expired_card`, `risk_block`, `network_timeout`, `issuer_decline`).
- 0ms latency, $0 compute cost.
- **Never cached** (rules execute instantaneously).

### Stage 2: In-Memory Diagnosis Cache
- In-memory fingerprint matching on `(error_code, error_reason, method, bank_name, bank_status)`.
- Eliminates redundant LLM calls when recurring failure patterns hit a batch.
- 0ms execution on cache hits with zero API calls.

### Stage 3: Primary AI (Groq)
- Model: `qwen/qwen3.8-27b` via Groq's ultra-low-latency LPU endpoint.
- Ingests payment failure attributes + deterministic bank health telemetry.
- Produces structured forensic analysis and confidence scoring.

### Stage 4: Deterministic Fallback & Guardrails
- If AI is unavailable or fails, gracefully falls back to `RootCause.UNKNOWN`.
- The downstream Policy Agent maps to `InterventionType.HOLD`.
- The Guardrail Agent safely quarantines the transaction to protect merchant spend caps.

---

## 2. Decision Agent

### Purpose
Choose recovery strategy based on diagnosed root cause.

### Policy Mapping
| Root Cause | Intervention |
| :--- | :--- |
| `insufficient_funds` | `retry_later` (allow time for account replenishment) |
| `network_timeout` | `retry_now` (immediate retry on transient switch blips) |
| `issuer_decline` | `suggest_alt_method` (recommend alternate card/UPI) |
| `expired_card` | `suggest_alt_method` (prompt user for updated card) |
| `risk_block` | `hold` (quarantine for manual compliance review) |
| `unknown` | `hold` (safety fallback quarantine) |

This stage remains 100% deterministic to guarantee auditability and regulatory compliance.

---

## 3. Guardrail Agent

### Purpose
Protect merchants from harmful actions, runaway retry fees, and spend limit breaches.

### Guardrail Constraints
- **Max Retries**: Max 3 retries per payment ID.
- **Cooldown Window**: 300 seconds (5 mins) minimum between immediate retries.
- **Batch Action Cap**: Max 20 retry actions per batch.
- **Batch Amount Cap**: Max ₹20,000 total retry volume per batch.

### Authority
The Guardrail Agent has unilateral authority to **Approve**, **Override**, or **Block** any proposed recovery action.

---

## 4. Executor Agent

### Purpose
Execute approved interventions and simulate real-world payment gateway responses.

### Possible Outcomes
- `recovered`: Payment succeeded and funds were won back.
- `still_failing`: Intervention attempted but payment failed again.
- `held`: Payment quarantined by policy or guardrail override.
- `unrecoverable`: Terminal failure (e.g. max retries exceeded).

---

## Auditability & Telemetry

Every agent execution step writes an immutable record to `AuditLog`:
- `payment_id`: Transaction identifier.
- `stage`: Agent stage (`diagnose`, `decide`, `stop_check`, `act`).
- `reasoning`: Complete plain-text explanation including forensic insights and bank telemetry.
- `confidence`: Diagnostic confidence score (0.0 to 1.0).
- `timestamp`: UTC timestamp.

### Audit Source Attribution
- `source = groq` (Marker: `⚡ AI Forensic:`)
- `source = cache` (Marker: `⚡ Cache Forensic:`)
- `source = deterministic_fallback` (Quarantine)
- `source = deterministic_rules` (Rule-based)