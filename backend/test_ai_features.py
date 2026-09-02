"""Test script verifying AI diagnostic features, mock bank health tool, and audit trail reconciliation."""

from app.database import SessionLocal, engine, Base
from app.models import BatchRun, Payment, PaymentStatus, RootCause, AuditLog, _id
from app.services.tools import get_bank_health, get_bank_health_for_payment
from app.services.classifier import detect_root_cause, classify_batch
from app.services.llm_classifier import AIDiagnosis


def test_bank_health_tool():
    print("--- 1. Testing Bank Health Tool ---")
    hdfc = get_bank_health("HDFC")
    assert hdfc["bank"] == "HDFC"
    assert hdfc["status"] == "degraded"
    assert hdfc["success_rate"] == 0.45
    print("[OK] HDFC bank health:", hdfc)

    icici = get_bank_health("ICICI")
    assert icici["bank"] == "ICICI"
    assert icici["status"] == "healthy"
    assert icici["success_rate"] == 0.98
    print("[OK] ICICI bank health:", icici)

    p = Payment(
        payment_id="test_pay_1",
        batch_id="batch_1",
        order_id="order_1",
        amount=50000,
        currency="INR",
        method="netbanking",
        error_code="GATEWAY_ERROR",
        error_reason="hdfc_timeout",
        status=PaymentStatus.FAILED,
    )
    p_health = get_bank_health_for_payment(p)
    assert p_health["bank"] == "HDFC"
    print("[OK] Payment bank health lookup:", p_health)

def test_ai_diagnosis_formatting():
    print("\n--- 2. Testing AI Diagnosis Reasoning & Audit Format ---")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create a payment with ambiguous/unknown error to trigger AI diagnosis
        batch_id = _id()
        batch = BatchRun(batch_id=batch_id, total=1)
        db.add(batch)
        
        payment = Payment(
            payment_id=_id(),
            batch_id=batch_id,
            order_id=f"order_{_id()}",
            amount=150000,
            currency="INR",
            method="upi",
            error_code="GATEWAY_ERROR",
            error_reason="unknown_error",
            status=PaymentStatus.FAILED,
            retry_count=0,
        )
        db.add(payment)
        db.commit()

        total, breakdown = classify_batch(db, batch_id)
        assert total == 1
        print("[OK] Classify batch completed. Breakdown:", breakdown)

        audit = db.query(AuditLog).filter(AuditLog.payment_id == payment.payment_id, AuditLog.stage == "diagnose").first()
        assert audit is not None
        print("[OK] Diagnose audit entry:", audit.reasoning.encode("ascii", "replace").decode("ascii"))
        assert "Root cause:" in audit.reasoning

    finally:
        db.close()

if __name__ == "__main__":
    test_bank_health_tool()
    test_ai_diagnosis_formatting()
    print("\n[SUCCESS] All AI visibility feature tests passed!")
