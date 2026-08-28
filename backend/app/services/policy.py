from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Intervention,
    InterventionType,
    Payment,
    RootCause,
    _id,
)

CAUSE_TO_INTERVENTION = {
    RootCause.INSUFFICIENT_FUNDS: InterventionType.RETRY_LATER,
    RootCause.ISSUER_DECLINE: InterventionType.SUGGEST_ALT_METHOD,
    RootCause.NETWORK_TIMEOUT: InterventionType.RETRY_NOW,
    RootCause.EXPIRED_CARD: InterventionType.SUGGEST_ALT_METHOD,
    RootCause.RISK_BLOCK: InterventionType.HOLD,
    RootCause.UNKNOWN: InterventionType.HOLD,
}


@dataclass(frozen=True)
class PolicyDecision:
    intervention_type: InterventionType
    reasoning: str


def decide_intervention(
    payment: Payment,
    confidence: float | None = None,
) -> PolicyDecision:
    """Deterministic policy mapping. Stopping rules live in guardrails."""
    retry_count = payment.retry_count or 0
    root_cause = payment.root_cause
    mapped = CAUSE_TO_INTERVENTION.get(root_cause, InterventionType.HOLD)
    return PolicyDecision(
        intervention_type=mapped,
        reasoning=(
            f"Root cause: {_cause_label(root_cause)}. "
            f"Chosen intervention: {mapped.value}. "
            f"retry_count={retry_count}. "
            f"{_mapping_reason(root_cause, mapped)}"
        ),
    )


def decide_batch(db: Session, batch_id: str) -> tuple[int, dict[str, int]]:
    """Decide an intervention for every payment in a batch. No execution."""
    payments = db.query(Payment).filter(Payment.batch_id == batch_id).all()
    breakdown: Counter[str] = Counter()

    for payment in payments:
        confidence = _latest_diagnose_confidence(db, payment.payment_id)
        decision = decide_intervention(payment, confidence=confidence)

        db.add(
            Intervention(
                intervention_id=_id(),
                payment_id=payment.payment_id,
                type=decision.intervention_type,
                outcome=None,
                razorpay_ref=None,
            )
        )
        db.add(
            AuditLog(
                entry_id=_id(),
                payment_id=payment.payment_id,
                stage="decide",
                reasoning=decision.reasoning,
                confidence=confidence,
            )
        )
        breakdown[decision.intervention_type.value] += 1

    db.commit()
    return len(payments), dict(breakdown)


def _latest_diagnose_confidence(db: Session, payment_id: str) -> float | None:
    entry = (
        db.query(AuditLog)
        .filter(AuditLog.payment_id == payment_id, AuditLog.stage == "diagnose")
        .order_by(AuditLog.timestamp.desc())
        .first()
    )
    if entry is None:
        return None
    return entry.confidence


def _cause_label(root_cause: RootCause | None) -> str:
    if root_cause is None:
        return "unclassified"
    return root_cause.value


def _mapping_reason(root_cause: RootCause | None, intervention: InterventionType) -> str:
    if root_cause is None:
        return "No classified root cause; defaulting to hold."
    reasons = {
        RootCause.INSUFFICIENT_FUNDS: (
            "Insufficient funds: delay retry so the customer can fund the account."
        ),
        RootCause.ISSUER_DECLINE: (
            "Issuer declined: retrying the same method is unlikely; suggest an alternate method."
        ),
        RootCause.NETWORK_TIMEOUT: (
            "Transient network/timeout: retry immediately is allowed."
        ),
        RootCause.EXPIRED_CARD: (
            "Expired card: the same instrument cannot succeed; suggest an alternate method."
        ),
        RootCause.RISK_BLOCK: (
            "Risk block: do not retry automatically; hold for review."
        ),
        RootCause.UNKNOWN: (
            "Unknown cause: do not take a money action; hold."
        ),
    }
    return reasons.get(root_cause, f"Mapped to {intervention.value}.")
