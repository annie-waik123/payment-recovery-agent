# Payment Recovery Agent — Full Architecture
Razorpay Buildathon, Track 3: AI Revenue Recovery
Payment Degradation → Root Cause → Recovery Action
Solo dev, 16 days · FastAPI + React + SQLite/SQLAlchemy · LangGraph optional

Status: FastAPI running, SQLite connected via SQLAlchemy, `Payment` +
`AuditLog` models built, seed endpoint working. This document is the
single reference for everything from here forward.

---

## 1. System architecture

Four layers, deliberately thin at the edges and strict in the middle:

**Ingestion** — three sources feeding the same pipeline: a Razorpay
webhook listener (`payment.failed`), a reconciliation poller (catches
events the webhook missed — a real Failure Recovery point, not trusting a
single delivery path), and a synthetic seeder for demo batches. Only the
seeder is required to be real from day one; the other two are optional
polish (see §9).

**Agent core** — three single-responsibility stages, never merged:
- *Classifier*: rules-first root-cause tagging (error_code + error_reason
  → taxonomy), with an LLM fallback only for the residual "unknown"
  bucket, returning a confidence score.
- *Policy engine*: pure function, (root cause, retry state, confidence) →
  intervention. No AI here — deterministic and auditable on purpose. This
  is what makes "every money action explainable, bounded and gated" true
  rather than asserted.
- *Executor*: the only component allowed to call Razorpay. Everything
  upstream of it is a recommendation.

**Guardrail layer** — stopping rules (max retries, cooldown windows), a
hard spend/action cap per batch, and the audit writer. Sits between
policy and executor so a bad decision is blocked before it touches money,
not just logged after.

**Serving** — FastAPI REST endpoints over SQLite, React dashboard polling
`GET /batches/{id}` (upgrade to SSE only if polling visibly lags).

LangGraph is optional and only earns its keep if you model the
classify → decide → act → check-stopping-rule loop as a graph with an
explicit conditional self-edge. A plain Python orchestrator loop demos
identically and is more legible to a judge reading code — don't reach for
the framework just because the track says "agent."

---

## 2. Database schema (SQLAlchemy)

Four tables. `Payment` and `AuditLog` already exist — add `batch_id` to
both now if they don't have it yet; retrofitting a foreign key onto
seeded rows later is more friction than adding it before real data
exists. `Intervention` and `BatchRun` are new.

```python
# app/db/models.py
import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from .base import Base


def _id() -> str:
    return uuid.uuid4().hex[:12]


class PaymentStatus(str, enum.Enum):
    FAILED = "failed"
    RETRYING = "retrying"
    RECOVERED = "recovered"
    UNRECOVERABLE = "unrecoverable"


class RootCause(str, enum.Enum):
    INSUFFICIENT_FUNDS = "insufficient_funds"
    ISSUER_DECLINE = "issuer_decline"
    NETWORK_TIMEOUT = "network_timeout"
    EXPIRED_CARD = "expired_card"
    RISK_BLOCK = "risk_block"
    UNKNOWN = "unknown"


class InterventionType(str, enum.Enum):
    RETRY_NOW = "retry_now"
    RETRY_LATER = "retry_later"
    SUGGEST_ALT_METHOD = "suggest_alt_method"
    HOLD = "hold"
    UNRECOVERABLE = "unrecoverable"


class Payment(Base):
    __tablename__ = "payments"
    payment_id = Column(String, primary_key=True, default=_id)
    batch_id = Column(String, ForeignKey("batch_runs.batch_id"), nullable=False)
    order_id = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)          # paise
    currency = Column(String, default="INR")
    method = Column(String, nullable=False)
    error_code = Column(String, nullable=False)
    error_reason = Column(Text, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.FAILED)
    root_cause = Column(Enum(RootCause), nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    interventions = relationship("Intervention", back_populates="payment")
    audit_entries = relationship("AuditLog", back_populates="payment")


class Intervention(Base):
    __tablename__ = "interventions"
    intervention_id = Column(String, primary_key=True, default=_id)
    payment_id = Column(String, ForeignKey("payments.payment_id"), nullable=False)
    type = Column(Enum(InterventionType), nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow)
    outcome = Column(String, nullable=True)             # recovered | still_failing | held | flagged
    razorpay_ref = Column(String, nullable=True)         # null while mocked

    payment = relationship("Payment", back_populates="interventions")


class AuditLog(Base):
    __tablename__ = "audit_log"
    entry_id = Column(String, primary_key=True, default=_id)
    payment_id = Column(String, ForeignKey("payments.payment_id"), nullable=False)
    stage = Column(String, nullable=False)               # detect|diagnose|decide|act|stop_check
    reasoning = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)             # only set on LLM-fallback path
    timestamp = Column(DateTime, default=datetime.utcnow)

    payment = relationship("Payment", back_populates="audit_entries")


class BatchRun(Base):
    __tablename__ = "batch_runs"
    batch_id = Column(String, primary_key=True, default=_id)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    total = Column(Integer, default=0)
    recovered = Column(Integer, default=0)
    unrecoverable = Column(Integer, default=0)
    recovery_rate = Column(Float, default=0.0)
```

Design choices worth defending to a judge:
- `AuditLog.reasoning` is a plain sentence, not a JSON blob — judges read
  the demo screen, not your database.
- `confidence` is nullable because the policy engine is deterministic;
  only the classifier's LLM-fallback path produces a real score. Never
  fabricate a confidence number for a rule match.
- `Intervention` is separate from `Payment` so one payment can have N
  intervention rows across retries — this *is* your Failure Recovery
  evidence, not an afterthought.

---

## 3. Agent boundaries

The line that most separates a winning submission from an impressive-but-
forgettable demo:

| Component | Owns | Never does |
|---|---|---|
| Classifier | Assigning a root cause + confidence | Deciding what action to take |
| Policy engine | Mapping (root cause, retry state, confidence) → intervention | Calling any external API |
| Executor | Calling Razorpay, recording the result | Deciding *whether* to act |
| Guardrail | Enforcing stop conditions and spend caps | Being skippable by any other component |

As real service modules:

```
services/
  classifier.py   detect_root_cause(payment) -> (RootCause, reasoning, confidence|None)
  policy.py       decide_intervention(payment) -> (InterventionType, reasoning)
  executor.py     execute(payment, intervention, db) -> outcome string
  orchestrator.py runs the loop over a batch, calling the three above in
                  order and writing AuditLog rows after every stage
```

Rules that keep these boundaries real, not just documented:
- `classifier.py` and `policy.py` never import anything from
  `executor.py` or touch a Razorpay client — pure decision logic,
  unit-testable without a network.
- `executor.py` is the *only* file that imports a Razorpay SDK/client.
- `orchestrator.py` is the only place that calls `executor.execute()` —
  no shortcut from classifier straight to action.
- Confidence-gated fallback: classifier tries rules first; only on
  `RootCause.UNKNOWN` does it call an LLM. If returned confidence is below
  threshold (e.g. 0.6), `policy.py` must map that straight to `HOLD`
  regardless of what the LLM guessed — enforce this in `policy.py`, not by
  trusting the classifier to self-limit. This one rule is the clearest
  answer you can give a judge who asks "what stops the AI from doing
  something dumb with money."

---

## 4. API design

```
POST   /batches                        create a batch, seed N failed payments
POST   /batches/{batch_id}/run          run detect→diagnose→decide→act loop
GET    /batches/{batch_id}              batch summary (total/recovered/rate)
GET    /batches                         list all batch runs (past-runs view)

GET    /payments?batch_id=&status=      filter payments
GET    /payments/{payment_id}           single payment + its interventions
POST   /payments/{payment_id}/override  manual stop/force-recover (human override)

GET    /audit?payment_id=&batch_id=     audit trail, filterable
GET    /metrics/{batch_id}              root-cause breakdown, confidence histogram
```

Keep `run` synchronous — 50-record batches finish in low seconds against
SQLite. No background workers or websockets until polling visibly lags in
the demo; don't build infrastructure a judge can't see the value of.

---

## 5. Folder structure

```
payment-recovery-agent/
  app/
    main.py                 # FastAPI app, router includes only
    core/
      config.py              # settings: retry limits, confidence threshold
    db/
      base.py                 # SQLAlchemy Base, session factory
      models.py                # tables from §2
    schemas/
      payment.py               # Pydantic request/response models
      batch.py
      audit.py
    services/
      classifier.py
      policy.py
      executor.py               # Razorpay client lives here, nowhere else
      orchestrator.py
      seed.py                    # synthetic batch generator
    api/
      routers/
        batches.py
        payments.py
        audit.py
        metrics.py
    tests/
      test_classifier.py         # pure logic, no DB — write these first
      test_policy.py
      test_orchestrator.py       # integration, in-memory SQLite
  frontend/                      # React, added last
  requirements.txt
  README.md
```

Router files stay thin — parse request, call a service function, return
response. Business logic in a router file is a sign it belongs in
`services/` instead.

---

## 6. Dashboard metrics (React, built last)

- **Headline**: recovery rate (recovered / total), amount recovered (₹),
  updating live as the batch runs
- **Root cause breakdown**: bar chart, count per cause — doubles as
  Problem Taste evidence, since it shows failures aren't treated as one
  undifferentiated bucket
- **Exception list**: every unrecoverable payment with its final
  reasoning line, visible and scrollable — your Failure Recovery proof
- **Audit trail viewer**: click a payment, see its full
  detect→diagnose→decide→act timeline in plain sentences
- **Confidence distribution**: LLM-fallback path only — a histogram
  showing most classifications are high-confidence rule matches, a thin
  tail is LLM-assisted. Answers "is this just an LLM wrapper" before a
  judge has to ask it.

Skip: auth, settings pages, multi-batch historical comparison — nothing
that isn't on screen during the demo.

---

## 7. Build order

1. **Finalize schema + migrate seed endpoint** to write into
   `batch_id`-scoped tables. Nothing else starts until seeding is clean.
2. **`classifier.py` rules path**, tested against your seed data's real
   error_code/error_reason combos — no LLM yet. Confirm every seeded
   scenario tags correctly before adding fallback complexity.
3. **`policy.py`** — deterministic, including the stopping rule
   (`retry_count >= MAX_RETRIES → UNRECOVERABLE`) and the confidence gate.
   Unit test in isolation; this is your most-scrutinized logic.
4. **`executor.py` mocked** — same interface it'll have with real
   Razorpay calls, simulated outcomes. Lets `orchestrator.py` and the API
   layer get built and demoable before integration risk shows up.
5. **`orchestrator.py` + `/batches/{id}/run`** — wire the full loop,
   confirm `AuditLog` rows are written at every stage with readable
   reasoning strings.
6. **Real Razorpay test-mode integration** inside `executor.py` — swap
   the mock, keep the same function signature. Do this once the rest of
   the pipeline is provably correct, so integration bugs don't hide
   behind logic bugs.
7. **LLM fallback** in `classifier.py` for the `UNKNOWN` bucket, with
   confidence scoring wired to the policy gate from step 3.
8. **React dashboard** — batch view, root-cause chart, exception list,
   audit drill-down. Last on purpose: a correct backend with no UI still
   demos via `/docs`; a polished UI over broken logic does not.

Remaining days beyond this core sequence: more Razorpay test-mode
scenario coverage, demo script rehearsal (show one full audit trail, not
just a summary chart), and a deliberate failure-mode demo — one payment
that correctly gets flagged unrecoverable instead of retried forever.
That single moment does more for Failure Recovery scoring than any chart.

---

## 8. Mock vs. real

| Component | Status | Why |
|---|---|---|
| Seed endpoint | **Real** (already built) | Only reliable data source without live Razorpay traffic |
| Classifier rules | **Real** | Core IP of the submission, zero external dependency |
| Policy engine | **Real** | Must be deterministic and inspectable regardless of integration status |
| Executor — retry/action calls | **Mocked**, until step 6 | Highest integration risk; build against a stable interface first |
| Executor — real Razorpay test-mode | **Real**, added step 6 | Needed for "actually works against Razorpay" credibility, once logic is solid |
| Webhook listener for live events | **Mocked / optional** | Seed endpoint covers the demo; a real webhook needs a public endpoint (ngrok etc.) — only worth it if time remains after step 7 |
| LLM classification fallback | **Real, but scoped** | Only for the residual unknown-cause bucket, never for the policy decision itself |
| Confidence threshold gating | **Real** | The exact line judges will probe — never mock the safety behavior |

The discipline that matters most across all of this: **the mock executor
and the real executor share an identical function signature and return
shape** — `execute_intervention(payment, intervention) -> outcome_str`
from day one. Swapping mock for real Razorpay calls in step 6 then
touches one file and changes zero callers, which is exactly the kind of
clean seam a judge reading your code will notice.

---

## 9. What NOT to build

- **A job queue / task broker** (Celery, RQ, etc.) — batch sizes here are
  50+ records, not 50,000. Synchronous FastAPI handles it.
- **User auth / multi-tenant anything** — single-operator demo, not a
  SaaS product.
- **A generic "AI does everything" agent** — an LLM deciding both root
  cause *and* action with no policy table in between is the fastest way to
  lose AI Judgement points.
- **Postgres / cloud deployment** — SQLite is fine for a demo; migrating
  databases mid-buildathon risks your one working system for a checkbox
  nobody's scoring.
- **A polished onboarding flow, landing page, or marketing copy** — spend
  the design budget on the exception list and audit trail readability.
- **A configurable rules UI** — hardcode the policy table in code with
  comments.
- **Real-money mode or anything offense-adjacent** — stay strictly inside
  Razorpay test-mode.
- **A manual-override UI beyond a single API endpoint** —
  `POST /payments/{id}/override` is enough to show you thought about human
  override; a full review-queue product is scope you don't have days for.