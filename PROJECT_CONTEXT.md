# Payment Recovery Agent

## Hackathon
Razorpay Buildathon 2026

Track:
AI Revenue Recovery

Sub-direction:
Payment Degradation → Root Cause → Recovery Action


# Problem

Merchants lose revenue because payments fail.

Current systems only show:
- payment failed
- error code

They don't explain:
- why it failed
- what action should happen
- whether recovery is safe


# Solution

Build an agentic payment recovery system.

The system:

1. Detects failed payments
2. Diagnoses root cause
3. Selects recovery strategy
4. Executes bounded action
5. Records complete audit trail


# Architecture

Flow:

Failed Payment
        |
        ↓
Classifier
        |
        ↓
Policy Engine
        |
        ↓
Guardrails
        |
        ↓
Executor
        |
        ↓
Audit Trail


# Agent Responsibilities


## Classifier

Purpose:
Understand why payment failed.

Input:
- error_code
- error_reason

Output:
- root_cause
- reasoning
- confidence

Important:
Rules first.
LLM only for unknown cases.


## Policy Engine

Purpose:
Decide what action is allowed.

Input:
- root cause
- retry count
- confidence

Output:
- intervention type

Must be deterministic.

Never use LLM for money decisions.


## Executor

Purpose:
Perform action.

Only component allowed to call Razorpay APIs.

Currently:
Mock executor.

Later:
Razorpay test mode.


## Audit System

Every decision must be explainable.

Example:

Payment failed because:
"Bank timeout detected"

Decision:
"Retry once after cooldown"

Result:
"Recovered"


# Tech Stack

Backend:
FastAPI

Database:
SQLite + SQLAlchemy

Frontend:
React

AI:
Rules first
LLM fallback later

Agent framework:
LangGraph optional


# Database

Tables:

Payment

Intervention

AuditLog

BatchRun


# Current Progress

Completed:

[x] FastAPI setup
[x] SQLite connection
[x] Basic models
[x] Seed endpoint started


Next:

1. Finalize database schema
2. Build classifier
3. Build policy engine
4. Build mock executor
5. Build orchestrator
6. Add Razorpay test integration
7. Build dashboard


# Development Rules

Do not:
- Build unnecessary complexity
- Add queues
- Add authentication
- Use LLM for decisions
- Build UI before backend works

Prioritize:
- Working demo
- Explainability
- Audit trail
- Recovery metrics