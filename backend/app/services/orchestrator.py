from datetime import datetime
from sqlalchemy.orm import Session
from app.models import BatchRun, Payment, PaymentStatus, Intervention
from app.services.classifier import classify_batch
from app.services.policy import decide_batch
from app.services.guardrails import guard_batch
from app.services.executor import execute_intervention

def run_batch_recovery(db: Session, batch_id: str) -> dict:
    """Run the complete agentic pipeline over the specified batch.

    1. Diagnose (Classifier)
    2. Decide (Policy Engine)
    3. Gate (Guardrails)
    4. Act (Executor)
    5. Update BatchRun metrics
    """
    # 1. Run Classification (Diagnose)
    classify_batch(db, batch_id)

    # 2. Run Policy Engine (Decide)
    decide_batch(db, batch_id)

    # 3. Run Guardrails (Gate)
    guard_batch(db, batch_id)

    # 4. Run Executor (Act)
    payments = db.query(Payment).filter(Payment.batch_id == batch_id).all()
    for payment in payments:
        # Find the latest intervention created/gated in the previous steps
        intervention = (
            db.query(Intervention)
            .filter(Intervention.payment_id == payment.payment_id)
            .order_by(Intervention.executed_at.desc())
            .first()
        )
        if intervention:
            execute_intervention(db, payment, intervention)

    # 5. Update BatchRun metrics
    batch = db.query(BatchRun).filter(BatchRun.batch_id == batch_id).first()
    if batch:
        total = len(payments)
        recovered = db.query(Payment).filter(
            Payment.batch_id == batch_id,
            Payment.status == PaymentStatus.RECOVERED
        ).count()
        unrecoverable = db.query(Payment).filter(
            Payment.batch_id == batch_id,
            Payment.status == PaymentStatus.UNRECOVERABLE
        ).count()

        batch.recovered = recovered
        batch.unrecoverable = unrecoverable
        batch.recovery_rate = (recovered / total) if total > 0 else 0.0
        batch.finished_at = datetime.utcnow()
        db.add(batch)
        db.commit()

        return {
            "batch_id": batch.batch_id,
            "total": batch.total,
            "recovered": batch.recovered,
            "unrecoverable": batch.unrecoverable,
            "recovery_rate": batch.recovery_rate,
            "finished_at": batch.finished_at
        }
    return {}
