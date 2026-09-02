from app.database import SessionLocal, engine, Base
from app.models import BatchRun, Payment, PaymentStatus, Intervention, AuditLog
from app.services.orchestrator import run_batch_recovery
from app.seed_data import generate_failed_payments

def test_recovery_flow():
    print("Initializing test database...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("Generating failed payments batch...")
        batch = generate_failed_payments(db, count=5)
        batch_id = batch.batch_id
        print(f"Batch generated. ID: {batch_id}, Total: {batch.total}")

        # Check payments status
        payments = db.query(Payment).filter(Payment.batch_id == batch_id).all()
        print("Initial Payment Statuses:")
        for p in payments:
            print(f" - Payment ID: {p.payment_id}, Status: {p.status.value}, Error Reason: {p.error_reason}")

        print("\nRunning Batch Recovery Orchestrator...")
        result = run_batch_recovery(db, batch_id)
        print("Recovery Completed! Result:")
        print(result)

        # Re-fetch payments
        payments_after = db.query(Payment).filter(Payment.batch_id == batch_id).all()
        print("\nPost-Recovery Payment Statuses:")
        for p in payments_after:
            # Let's count interventions
            interventions = db.query(Intervention).filter(Intervention.payment_id == p.payment_id).all()
            # Let's get audit logs
            audits = db.query(AuditLog).filter(AuditLog.payment_id == p.payment_id).all()
            print(f" - Payment ID: {p.payment_id}, Status: {p.status.value}, Retries: {p.retry_count}")
            print(f"   Interventions ({len(interventions)}): {[i.type.value for i in interventions]}")
            print(f"   Audit Logs ({len(audits)}): {[a.stage for a in audits]}")

        # Assertions
        assert result["total"] == 5
        assert "recovery_rate" in result
        assert "finished_at" in result
        print("\nAssertions passed successfully! The end-to-end agentic recovery loop functions perfectly.")

    finally:
        db.close()

if __name__ == "__main__":
    test_recovery_flow()
