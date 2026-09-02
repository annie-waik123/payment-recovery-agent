from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import AuditLog, Payment, RootCause, _id
from app.services.llm_classifier import classify_with_fallback
from app.services.tools import get_bank_health_for_payment


@dataclass(frozen=True)
class ClassificationResult:
    root_cause: RootCause
    reasoning: str
    confidence: float | None
    source: str = "deterministic_rules"


def detect_root_cause(payment: Payment) -> ClassificationResult:
    """Diagnostic Hierarchy:
    1. Deterministic Rules (85% known patterns, 0 token cost, never cached)
    2. Diagnosis Cache (in-memory fingerprint matching)
    3. Primary AI: Groq (qwen/qwen3.8-27b on OpenAI-compatible endpoint)
    4. Deterministic Fallback (quarantine + guardrails containment)
    """
    reason = (payment.error_reason or "").lower()
    code = (payment.error_code or "").upper()

    # --- Stage 1: Deterministic Rules (Never cached) ---
    if _is_insufficient_funds(reason, code):
        return ClassificationResult(
            root_cause=RootCause.INSUFFICIENT_FUNDS,
            reasoning=(
                "Root cause: insufficient_funds. "
                f"error_code={payment.error_code} error_reason={payment.error_reason} "
                "matched insufficient-funds rules. [Source: deterministic_rules]"
            ),
            confidence=1.0,
            source="deterministic_rules",
        )

    if _is_expired_card(reason, code):
        return ClassificationResult(
            root_cause=RootCause.EXPIRED_CARD,
            reasoning=(
                "Root cause: expired_card. "
                f"error_code={payment.error_code} error_reason={payment.error_reason} "
                "matched expired-card rules. [Source: deterministic_rules]"
            ),
            confidence=1.0,
            source="deterministic_rules",
        )

    if _is_risk_block(reason, code):
        return ClassificationResult(
            root_cause=RootCause.RISK_BLOCK,
            reasoning=(
                "Root cause: risk_block. "
                f"error_code={payment.error_code} error_reason={payment.error_reason} "
                "matched risk-engine / risk-check rules. [Source: deterministic_rules]"
            ),
            confidence=1.0,
            source="deterministic_rules",
        )

    if _is_network_timeout(reason, code):
        return ClassificationResult(
            root_cause=RootCause.NETWORK_TIMEOUT,
            reasoning=(
                "Root cause: network_timeout. "
                f"error_code={payment.error_code} error_reason={payment.error_reason} "
                "matched timeout / network-error rules. [Source: deterministic_rules]"
            ),
            confidence=1.0,
            source="deterministic_rules",
        )

    if _is_issuer_decline(reason, code):
        return ClassificationResult(
            root_cause=RootCause.ISSUER_DECLINE,
            reasoning=(
                "Root cause: issuer_decline. "
                f"error_code={payment.error_code} error_reason={payment.error_reason} "
                "matched bank/issuer decline rules. [Source: deterministic_rules]"
            ),
            confidence=1.0,
            source="deterministic_rules",
        )

    # --- Stage 2-4: Residual Unknown Escalation (Cache -> Groq AI -> Deterministic Fallback) ---
    bank_health = get_bank_health_for_payment(payment)
    bank_tag = f" [Bank Health: {bank_health['bank']} {int(bank_health['success_rate']*100)}% SR - {bank_health['status'].capitalize()}]"

    ai_result, source = classify_with_fallback(payment, bank_health)

    if ai_result is not None:
        marker = "⚡ AI Forensic:" if source == "groq" else "⚡ Cache Forensic:"
        return ClassificationResult(
            root_cause=RootCause(ai_result.root_cause),
            # "Root cause: X (...)." prefix is load-bearing -- the dashboard's
            # frontend parser extracts root cause from exactly this phrase.
            reasoning=(
                f"Root cause: {ai_result.root_cause} (confidence={ai_result.confidence:.2f}). "
                f"{marker} {ai_result.forensic_reasoning}{bank_tag} [Source: {source}]"
            ),
            confidence=ai_result.confidence,
            source=source,
        )

    return ClassificationResult(
        root_cause=RootCause.UNKNOWN,
        reasoning=(
            "Root cause: unknown. "
            f"error_code={payment.error_code} error_reason={payment.error_reason} "
            "did not match any deterministic recovery taxonomy rule. "
            "AI escalation also failed to produce a diagnosis. "
            "[Source: deterministic_fallback]"
        ),
        confidence=None,
        source="deterministic_fallback",
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
