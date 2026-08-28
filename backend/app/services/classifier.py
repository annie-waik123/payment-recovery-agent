from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import AuditLog, Payment, RootCause, _id


@dataclass(frozen=True)
class ClassificationResult:
    root_cause: RootCause
    reasoning: str
    confidence: float | None


def detect_root_cause(payment: Payment) -> ClassificationResult:
    """Rules-only diagnosis from error_code + error_reason. No LLM."""
    reason = (payment.error_reason or "").lower()
    code = (payment.error_code or "").upper()

    if _is_insufficient_funds(reason, code):
        return ClassificationResult(
            root_cause=RootCause.INSUFFICIENT_FUNDS,
            reasoning=(
                "Root cause: insufficient_funds. "
                f"error_code={payment.error_code} error_reason={payment.error_reason} "
                "matched insufficient-funds rules."
            ),
            confidence=1.0,
        )

    if _is_expired_card(reason, code):
        return ClassificationResult(
            root_cause=RootCause.EXPIRED_CARD,
            reasoning=(
                "Root cause: expired_card. "
                f"error_code={payment.error_code} error_reason={payment.error_reason} "
                "matched expired-card rules."
            ),
            confidence=1.0,
        )

    if _is_risk_block(reason, code):
        return ClassificationResult(
            root_cause=RootCause.RISK_BLOCK,
            reasoning=(
                "Root cause: risk_block. "
                f"error_code={payment.error_code} error_reason={payment.error_reason} "
                "matched risk-engine / risk-check rules."
            ),
            confidence=1.0,
        )

    if _is_network_timeout(reason, code):
        return ClassificationResult(
            root_cause=RootCause.NETWORK_TIMEOUT,
            reasoning=(
                "Root cause: network_timeout. "
                f"error_code={payment.error_code} error_reason={payment.error_reason} "
                "matched timeout / network-error rules."
            ),
            confidence=1.0,
        )

    if _is_issuer_decline(reason, code):
        return ClassificationResult(
            root_cause=RootCause.ISSUER_DECLINE,
            reasoning=(
                "Root cause: issuer_decline. "
                f"error_code={payment.error_code} error_reason={payment.error_reason} "
                "matched bank/issuer decline rules."
            ),
            confidence=1.0,
        )

    return ClassificationResult(
        root_cause=RootCause.UNKNOWN,
        reasoning=(
            "Root cause: unknown. "
            f"error_code={payment.error_code} error_reason={payment.error_reason} "
            "did not match any deterministic recovery taxonomy rule."
        ),
        confidence=None,
    )


def classify_batch(db: Session, batch_id: str) -> tuple[int, dict[str, int]]:
    """Classify every payment in a batch, persist root_cause, write diagnose audits."""
    payments = db.query(Payment).filter(Payment.batch_id == batch_id).all()
    breakdown: Counter[str] = Counter()

    for payment in payments:
        result = detect_root_cause(payment)
        payment.root_cause = result.root_cause
        db.add(
            AuditLog(
                entry_id=_id(),
                payment_id=payment.payment_id,
                stage="diagnose",
                reasoning=result.reasoning,
                confidence=result.confidence,
            )
        )
        breakdown[result.root_cause.value] += 1

    db.commit()
    return len(payments), dict(breakdown)


def _is_insufficient_funds(reason: str, code: str) -> bool:
    return "insufficient" in reason or code in {"INSUFFICIENT_FUNDS"}


def _is_expired_card(reason: str, code: str) -> bool:
    return "expired" in reason or "card_expired" in reason or code in {"EXPIRED_CARD"}


def _is_risk_block(reason: str, code: str) -> bool:
    return (
        "risk" in reason
        or "blocked_by_risk" in reason
        or code in {"RISK_BLOCKED"}
    )


def _is_network_timeout(reason: str, code: str) -> bool:
    return (
        "timeout" in reason
        or "timed_out" in reason
        or "network" in reason
        or code in {"NETWORK_TIMEOUT"}
    )


def _is_issuer_decline(reason: str, code: str) -> bool:
    return (
        "declin" in reason
        or "issuer" in reason
        or "bank_declined" in reason
        or code in {"BANK_DECLINED"}
    )
