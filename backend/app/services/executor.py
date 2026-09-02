import random
from sqlalchemy.orm import Session
from app.models import Payment, Intervention, PaymentStatus, InterventionType, RootCause, AuditLog, _id

MONEY_ACTIONS = {InterventionType.RETRY_NOW, InterventionType.RETRY_LATER}

def execute_intervention(db: Session, payment: Payment, intervention: Intervention) -> str:
    """Mock execution of interventions. Simulates success rates depending on cause.

    Under hold, status is left unchanged.
    """
    cause = payment.root_cause
    itype = intervention.type

    outcome = "still_failing"

    if itype in MONEY_ACTIONS:
        payment.retry_count = (payment.retry_count or 0) + 1
        # Success probability based on root cause
        if cause == RootCause.NETWORK_TIMEOUT:
            success = random.random() < 0.8
        elif cause == RootCause.INSUFFICIENT_FUNDS:
            success = random.random() < 0.3
        elif cause == RootCause.ISSUER_DECLINE:
            success = random.random() < 0.15
        else:
            success = False

        if success:
            outcome = "recovered"
            payment.status = PaymentStatus.RECOVERED
        else:
            outcome = "still_failing"
            # Maintain retry state - if it fails, it is still retrying/failed
            payment.status = PaymentStatus.FAILED

    elif itype == InterventionType.SUGGEST_ALT_METHOD:
        payment.retry_count = (payment.retry_count or 0) + 1
        # Mock customer recovers by using another method (40% probability)
        success = random.random() < 0.4
        if success:
            outcome = "recovered"
            payment.status = PaymentStatus.RECOVERED
        else:
            outcome = "still_failing"
            payment.status = PaymentStatus.FAILED

    elif itype == InterventionType.HOLD:
        # User requested: HOLD interventions should not force status=FAILED.
        # Leave status unchanged (or RETRYING)
        outcome = "held"
        # We do not change payment.status here

    elif itype == InterventionType.UNRECOVERABLE:
        outcome = "still_failing"
        payment.status = PaymentStatus.UNRECOVERABLE

    intervention.outcome = outcome
    db.add(payment)
    db.add(intervention)

    # Write the execution audit log entry
    db.add(
        AuditLog(
            entry_id=_id(),
            payment_id=payment.payment_id,
            stage="act",
            reasoning=(
                f"Executed intervention {itype.value}. "
                f"Result: {outcome}. "
                f"New status: {payment.status.value}. "
                f"Retry count: {payment.retry_count}."
            ),
            confidence=None,
        )
    )
    db.commit()
    return outcome
