from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import (
    CONFIDENCE_HOLD_THRESHOLD,
    MAX_BATCH_RETRY_ACTIONS,
    MAX_BATCH_RETRY_AMOUNT_PAISE,
    MAX_RETRIES,
    RETRY_COOLDOWN_SECONDS,
)
from app.models import AuditLog, Intervention, InterventionType, Payment, _id

MONEY_ACTIONS = {
    InterventionType.RETRY_NOW,
    InterventionType.RETRY_LATER,
}


@dataclass
class BatchGuardState:
    retry_actions_used: int = 0
    retry_amount_used: int = 0


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    final_intervention: InterventionType
    reasoning: str
    block_reason: str | None = None


def evaluate_guardrail(
    payment: Payment,
    proposed: InterventionType,
    *,
    confidence: float | None = None,
    previous_interventions: list[Intervention] | None = None,
    batch_state: BatchGuardState | None = None,
    now: datetime | None = None,
) -> GuardrailResult:
    """Block or pass a policy recommendation. Never calls Razorpay."""
    previous_interventions = previous_interventions or []
    batch_state = batch_state or BatchGuardState()
    now = now or datetime.utcnow()
    retry_count = payment.retry_count or 0

    if retry_count >= MAX_RETRIES:
        return GuardrailResult(
            allowed=False,
            final_intervention=InterventionType.UNRECOVERABLE,
            block_reason="max_retries",
            reasoning=(
                f"Stop check blocked. retry_count={retry_count} "
                f">= MAX_RETRIES={MAX_RETRIES}. "
                f"Proposed {proposed.value} replaced with unrecoverable."
            ),
        )

    if (
        proposed in MONEY_ACTIONS
        and confidence is not None
        and confidence < CONFIDENCE_HOLD_THRESHOLD
    ):
        return GuardrailResult(
            allowed=False,
            final_intervention=InterventionType.HOLD,
            block_reason="low_confidence",
            reasoning=(
                f"Stop check blocked. confidence={confidence} "
                f"< {CONFIDENCE_HOLD_THRESHOLD}. "
                f"Proposed {proposed.value} replaced with hold."
            ),
        )

    if proposed == InterventionType.RETRY_NOW and _in_cooldown(
        previous_interventions, now
    ):
        return GuardrailResult(
            allowed=False,
            final_intervention=InterventionType.RETRY_LATER,
            block_reason="cooldown",
            reasoning=(
                f"Stop check blocked. retry_now is inside the "
                f"{RETRY_COOLDOWN_SECONDS}s cooldown window. "
                "Proposed retry_now replaced with retry_later."
            ),
        )

    if proposed in MONEY_ACTIONS:
        next_actions = batch_state.retry_actions_used + 1
        next_amount = batch_state.retry_amount_used + (payment.amount or 0)
        if next_actions > MAX_BATCH_RETRY_ACTIONS:
            return GuardrailResult(
                allowed=False,
                final_intervention=InterventionType.HOLD,
                block_reason="batch_action_cap",
                reasoning=(
                    f"Stop check blocked. Batch retry action cap "
                    f"{MAX_BATCH_RETRY_ACTIONS} would be exceeded. "
                    f"Proposed {proposed.value} replaced with hold."
                ),
            )
        if next_amount > MAX_BATCH_RETRY_AMOUNT_PAISE:
            return GuardrailResult(
                allowed=False,
                final_intervention=InterventionType.HOLD,
                block_reason="batch_spend_cap",
                reasoning=(
                    f"Stop check blocked. Batch retry spend cap "
                    f"{MAX_BATCH_RETRY_AMOUNT_PAISE} paise would be exceeded. "
                    f"Proposed {proposed.value} replaced with hold."
                ),
            )
        batch_state.retry_actions_used = next_actions
        batch_state.retry_amount_used = next_amount

    return GuardrailResult(
        allowed=True,
        final_intervention=proposed,
        reasoning=(
            f"Stop check passed. Proposed {proposed.value} is within "
            f"retry, cooldown, confidence, and batch spend/action limits."
        ),
    )


def guard_batch(db: Session, batch_id: str) -> dict:
    """Gate the latest policy intervention for every payment. No execution."""
    payments = db.query(Payment).filter(Payment.batch_id == batch_id).all()
    batch_state = BatchGuardState()
    allowed = 0
    blocked = 0
    final_breakdown: Counter[str] = Counter()
    block_breakdown: Counter[str] = Counter()

    for payment in payments:
        latest = _latest_intervention(db, payment.payment_id)
        if latest is None:
            continue

        previous = _previous_interventions(db, payment.payment_id, latest.intervention_id)
        confidence = _latest_diagnose_confidence(db, payment.payment_id)
        result = evaluate_guardrail(
            payment,
            latest.type,
            confidence=confidence,
            previous_interventions=previous,
            batch_state=batch_state,
        )

        if not result.allowed:
            latest.type = result.final_intervention
            blocked += 1
            if result.block_reason:
                block_breakdown[result.block_reason] += 1
        else:
            allowed += 1

        db.add(
            AuditLog(
                entry_id=_id(),
                payment_id=payment.payment_id,
                stage="stop_check",
                reasoning=result.reasoning,
                confidence=confidence,
            )
        )
        final_breakdown[result.final_intervention.value] += 1

    db.commit()
    checked = allowed + blocked
    return {
        "total_checked": checked,
        "allowed": allowed,
        "blocked": blocked,
        "intervention_breakdown": dict(final_breakdown),
        "block_reason_breakdown": dict(block_breakdown),
    }


def _in_cooldown(previous_interventions: list[Intervention], now: datetime) -> bool:
    cutoff = now - timedelta(seconds=RETRY_COOLDOWN_SECONDS)
    for item in previous_interventions:
        if item.type not in MONEY_ACTIONS:
            continue
        executed_at = item.executed_at
        if executed_at is not None and executed_at >= cutoff:
            return True
    return False


def _latest_intervention(db: Session, payment_id: str) -> Intervention | None:
    return (
        db.query(Intervention)
        .filter(Intervention.payment_id == payment_id)
        .order_by(Intervention.executed_at.desc())
        .first()
    )


def _previous_interventions(
    db: Session, payment_id: str, current_id: str
) -> list[Intervention]:
    return (
        db.query(Intervention)
        .filter(
            Intervention.payment_id == payment_id,
            Intervention.intervention_id != current_id,
        )
        .all()
    )


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
