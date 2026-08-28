import random

from app.models import BatchRun, Payment, PaymentStatus, _id

# Razorpay-style failure scenarios for later rules-based classification.
# (error_code, error_reason, method) — root_cause left unset in Step 1.
FAILURE_SCENARIOS = [
    ("BAD_REQUEST_ERROR", "insufficient_funds", "card"),
    ("BAD_REQUEST_ERROR", "payment_failed_due_to_insufficient_funds", "upi"),
    ("GATEWAY_ERROR", "bank_declined_transaction", "card"),
    ("GATEWAY_ERROR", "issuer_declined", "netbanking"),
    ("GATEWAY_ERROR", "payment_timed_out", "upi"),
    ("SERVER_ERROR", "network_error", "card"),
    ("BAD_REQUEST_ERROR", "card_expired", "card"),
    ("BAD_REQUEST_ERROR", "expired_card", "card"),
    ("BAD_REQUEST_ERROR", "payment_risk_check_failed", "card"),
    ("BAD_REQUEST_ERROR", "transaction_blocked_by_risk_engine", "wallet"),
    ("GATEWAY_ERROR", "unknown_error", "upi"),
    ("SERVER_ERROR", "internal_server_error", "netbanking"),
]

METHODS = ["card", "upi", "netbanking", "wallet"]


def generate_failed_payments(db, count: int = 50) -> BatchRun:
    """Create a BatchRun and N linked failed Payment rows. No recovery logic."""
    batch_id = _id()
    batch = BatchRun(
        batch_id=batch_id,
        total=count,
        recovered=0,
        unrecoverable=0,
        recovery_rate=0.0,
    )
    db.add(batch)

    for _ in range(count):
        error_code, error_reason, method = random.choice(FAILURE_SCENARIOS)
        # Prefer scenario method; occasionally vary method for realism.
        if random.random() < 0.2:
            method = random.choice(METHODS)

        payment = Payment(
            payment_id=_id(),
            batch_id=batch_id,
            order_id=f"order_{_id()}",
            amount=random.randint(10_000, 500_000),  # ₹100 – ₹5,000 in paise
            currency="INR",
            method=method,
            error_code=error_code,
            error_reason=error_reason,
            status=PaymentStatus.FAILED,
            root_cause=None,
            retry_count=0,
        )
        db.add(payment)

    db.commit()
    db.refresh(batch)
    return batch
