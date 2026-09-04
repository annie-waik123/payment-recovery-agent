# Payment Recovery Agent

AI-powered payment failure diagnosis and recovery platform built with FastAPI, React, and Groq.

The system automatically analyzes failed payments, identifies root causes, applies recovery strategies, enforces business guardrails, and generates a complete audit trail for every decision.


## Problem Statement

Payment failures create significant revenue leakage for businesses.

Traditional systems often:
- Retry blindly
- Lack explainability
- Provide poor diagnostics
- Have limited visibility into recovery outcomes

This project introduces an agentic recovery workflow that combines deterministic rules, AI-powered diagnosis, caching, and recovery automation.

## Key Features

- Multi-agent recovery pipeline
- Groq-powered forensic diagnosis
- Fingerprint-based diagnosis cache
- Deterministic payment intelligence
- Recovery strategy engine
- Business guardrails
- Revenue recovery analytics
- Complete audit trail
- Interactive dashboard
- Real-time incident simulation

## Architecture

### Agent Workflow

```text
Failed Payment
      │
      ▼
Classifier Agent
      │
      ▼
Decision Agent
      │
      ▼
Guardrail Agent
      │
      ▼
Executor Agent
      │
      ▼
Recovery Outcome
```

### AI Diagnostic Pipeline

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
Groq Diagnosis
      │
      ▼
Fallback Logic
```

## Agent Responsibilities

### Classifier Agent
Identifies payment failure root causes.

Examples:
- Insufficient funds
- Network timeout
- Issuer decline
- Expired card
- Risk block

### Decision Agent
Selects the optimal recovery strategy.

Examples:
- Retry now
- Retry later
- Escalate
- Alternative payment method

### Guardrail Agent
Applies business constraints and safety checks.

Examples:
- Confidence thresholds
- Risk controls
- Retry limitations
- Policy enforcement

### Executor Agent
Performs approved recovery actions and records outcomes.

## Dashboard Features

### Executive Summary
- Recovery rate
- Revenue recovered
- Revenue at risk
- Root cause distribution

### AI Diagnostics
- Rule vs AI decisions
- Cache hit statistics
- AI escalation coverage
- Diagnostic confidence

### Audit Trail
- Root cause analysis
- Recovery decisions
- AI reasoning
- Timestamps
- Recovery outcomes

## Tech Stack

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
- Fingerprint Cache

## Project Structure

```text
payment-recovery-agent/
│
├── backend/
│   └── app/
│
├── frontend/
│   ├── src/
│   └── public/
│
├── submission_assets/
│
├── ARCHITECTURE.md
├── PROJECT_CONTEXT.md
├── README.md
├── requirements.txt
└── .gitignore
```

## Installation

### Backend

```bash
python -m venv venv
```

Activate:

Windows

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
GROQ_API_KEY=your_api_key
```

Run backend:

```bash
cd backend
uvicorn app.main:app --reload
```

### Frontend

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

## Sample Results

```text
Payments Analyzed: 50
Recovered: 14
Recovery Rate: 28%
AI Diagnoses: 8
Cache Hits: 2
Revenue Recovered: ₹23,059
```

## Design Principles

- Explainability first
- Deterministic when possible
- AI only for ambiguity
- Safety before automation
- Full auditability
- Cost-efficient inference
- Low-latency recovery

## Future Enhancements

- Redis distributed cache
- Multiple payment gateway integrations
- Human approval workflows
- Predictive recovery optimization
- Multi-model routing
- Real payment gateway APIs

## Author

**Waikhom Annithoi**

Computer Engineering Student

Built for intelligent payment failure diagnosis, recovery automation, and revenue protection using agentic AI workflows.
