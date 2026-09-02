# Payment Recovery Agent

An AI-powered payment recovery system that automatically diagnoses failed payments, applies recovery strategies, enforces guardrails, and provides a complete audit trail.

Built as a multi-agent workflow that combines deterministic payment intelligence, Groq-powered forensic diagnosis, fingerprint-based caching, and recovery automation.

---

## Overview

Payment failures are a major source of revenue leakage for businesses. This project analyzes failed transactions, identifies root causes, recommends recovery actions, and tracks outcomes through a transparent audit pipeline.

The system prioritizes:

- Fast diagnosis
- Explainable decisions
- Safe recovery actions
- Full auditability
- Low inference cost
- High reliability

---

## Architecture

### 1. Classifier Agent

Determines the root cause of a failed payment.

Examples:

- Insufficient funds
- Network timeout
- Issuer decline
- Risk block
- Expired card
- Unknown failure

### 2. Decision Agent

Selects the best recovery strategy.

Examples:

- Retry now
- Retry later
- Alternate payment method
- Escalation
- Hold transaction

### 3. Guardrail Agent

Applies business and safety constraints.

Examples:

- Batch spend limits
- Confidence thresholds
- Recovery policy checks
- Risk containment

### 4. Executor Agent

Performs the approved recovery action and records the result.

---

## AI Diagnostic Architecture

The project uses a streamlined Groq-only AI pipeline.

```text
Failed Payment
      │
      ▼
Deterministic Rules
      │
      ▼
Fingerprint Cache
      │
      ▼
Groq AI Diagnosis
      │
      ▼
Deterministic Fallback
```

### Deterministic Rules

Handles known payment failure patterns.

Examples:

- insufficient_funds
- expired_card
- issuer_decline
- network_timeout

### Fingerprint Cache

Previously diagnosed ambiguous failures are cached.

Benefits:

- 0ms retrieval
- No additional AI calls
- Reduced cost
- Consistent diagnoses

### Groq AI

Used only when deterministic rules cannot identify a root cause.

Provides:

- Forensic reasoning
- Context-aware diagnosis
- Recovery recommendations

### Deterministic Fallback

If AI becomes unavailable, the system safely quarantines the payment and marks it as:

```text
RootCause.UNKNOWN
```

---

## Key Features

- Multi-agent recovery workflow
- Groq-powered forensic diagnosis
- Fingerprint-based diagnosis cache
- Deterministic payment intelligence
- Recovery strategy engine
- Guardrail enforcement
- Revenue impact analytics
- Immutable audit trail
- Interactive dashboard
- Real-time incident simulation

---

## Dashboard Features

### Executive Summary

- Recovery rate
- Revenue recovered
- Revenue at risk
- Top root causes

### AI Diagnostics

- Rule vs AI breakdown
- AI escalation coverage
- Forensic confidence
- Cache hit statistics
- AI-attributed recovery revenue

### Agent Pipeline

Visual representation of:

```text
Failed Payment
→ Classifier
→ Decision Engine
→ Guardrails
→ Executor
→ Outcome
```

### Audit Trail

Provides:

- Root cause analysis
- Decision reasoning
- Recovery actions
- AI forensic insights
- Timestamps

---

## Technology Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- SQLite

### Frontend

- React
- Vite
- Recharts

### AI Layer

- Groq API
- Qwen Model
- In-Memory Fingerprint Cache

---

## Project Structure

```text
payment-recovery-agent/
│
├── backend/
│   ├── app/
│   ├── .env
│   ├── payment_recovery.db
│
├── frontend/
│   ├── src/
│   ├── dist/
│
├── submission_assets/
│
├── ARCHITECTURE.md
├── PROJECT_CONTEXT.md
├── README.md
├── requirements.txt
└── .gitignore
```

---

## Installation

### Clone Repository

```bash
git clone <repository-url>
cd payment-recovery-agent
```

### Backend Setup

```bash
python -m venv venv
```

Activate environment:

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create:

```bash
backend/.env
```

Add:

```env
GROQ_API_KEY=your_key_here
```

Start backend:

```bash
cd backend
uvicorn app.main:app --reload
```

---

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

Backend:

```text
http://localhost:8000
```

---

## Testing

Run verification suite:

```bash
python test_groq_cache_verification.py
```

Tests verify:

- Groq diagnosis path
- Cache hit path
- Deterministic fallback path
- Full batch reconciliation

---

## Example Results

Sample batch:

```text
Payments Analyzed: 50
Recovered: 14
Recovery Rate: 28%
AI Diagnoses: 8
Cache Hits: 2
Revenue Recovered: ₹23,059
```

---

## Design Principles

- Explainability first
- AI only for ambiguity
- Deterministic when possible
- Safety before automation
- Complete auditability
- Low latency
- Cost-efficient inference

---

## Future Enhancements

- Redis distributed cache
- Multiple payment gateway integrations
- Real bank telemetry APIs
- Human approval workflows
- Predictive recovery optimization
- Multi-model AI routing

---

## Author

Waikhom Annithoi

Computer Engineering Student

Built as an intelligent payment failure diagnosis and revenue recovery platform combining deterministic systems, agentic workflows, and Groq-powered forensic analysis.