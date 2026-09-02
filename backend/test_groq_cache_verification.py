"""Comprehensive verification for simplified Groq + Cache architecture:
- Test 1: First ambiguous failure -> source = groq
- Test 2: Repeat identical failure -> source = cache
- Test 3: Groq unavailable -> source = deterministic_fallback & RootCause.UNKNOWN
- Test 4: Full batch execution reporting exact breakdown (Rules, Cache, Groq, Fallback)
"""

from unittest.mock import patch
from app.database import SessionLocal, engine, Base
from app.models import Payment, PaymentStatus, RootCause, BatchRun
from app.services.diagnosis_cache import CACHE, CACHE_STATS, clear_cache, get_cache_stats
from app.services.classifier import detect_root_cause, classify_batch
from app.services.orchestrator import run_batch_recovery
from app.seed_data import generate_failed_payments

def run_all_tests():
    print("================================================================")
    print("RUNNING FINAL ARCHITECTURE VERIFICATION: GROQ + CACHE ONLY")
    print("================================================================")

    # -------------------------------------------------------------
    # Test 1: First ambiguous failure -> source = groq
    # -------------------------------------------------------------
    clear_cache()
    pay_1 = Payment(
        payment_id="test_pay_ambiguous_1",
        amount=250000,
        currency="INR",
        method="netbanking",
        error_code="GATEWAY_ERROR",
        error_reason="hdfc_switch_unknown",
        status=PaymentStatus.FAILED,
    )
    res_1 = detect_root_cause(pay_1)
    print("\n--- TEST 1: First Ambiguous Failure ---")
    print(f"Payment ID: {pay_1.payment_id}")
    print(f"Diagnosed Root Cause: {res_1.root_cause.value}")
    print(f"Confidence: {res_1.confidence}")
    print(f"Source: {res_1.source}")
    print(f"Reasoning: {res_1.reasoning.encode('ascii', 'replace').decode('ascii')}")
    assert res_1.source == "groq", f"Expected source='groq', got '{res_1.source}'"
    assert len(CACHE) == 1, f"Expected cache size=1, got {len(CACHE)}"
    print(">> [PASS] Test 1: First ambiguous failure diagnosed via Groq AI.")

    # -------------------------------------------------------------
    # Test 2: Repeat identical failure -> source = cache
    # -------------------------------------------------------------
    pay_2 = Payment(
        payment_id="test_pay_ambiguous_2",
        amount=150000,
        currency="INR",
        method="netbanking",
        error_code="GATEWAY_ERROR",
        error_reason="hdfc_switch_unknown",
        status=PaymentStatus.FAILED,
    )
    initial_hits = get_cache_stats()["hits"]
    with patch("app.services.llm_classifier.classify_with_groq", side_effect=Exception("Should not be called")) as mock_groq:
        res_2 = detect_root_cause(pay_2)
        mock_groq.assert_not_called()
    print("\n--- TEST 2: Repeat Identical Failure (Cache Test) ---")
    print(f"Payment ID: {pay_2.payment_id}")
    print(f"Diagnosed Root Cause: {res_2.root_cause.value}")
    print(f"Source: {res_2.source}")
    print(f"Reasoning: {res_2.reasoning.encode('ascii', 'replace').decode('ascii')}")
    print(f"Cache Stats: {get_cache_stats()}")
    assert res_2.source == "cache", f"Expected source='cache', got '{res_2.source}'"
    assert get_cache_stats()["hits"] == initial_hits + 1
    print(">> [PASS] Test 2: Identical failure hit cache with 0 API calls.")

    # -------------------------------------------------------------
    # Test 3: Groq unavailable -> source = deterministic_fallback
    # -------------------------------------------------------------
    clear_cache()
    pay_3 = Payment(
        payment_id="test_pay_fallback",
        amount=500000,
        currency="INR",
        method="card",
        error_code="SERVER_ERROR",
        error_reason="unmapped_500_error",
        status=PaymentStatus.FAILED,
    )
    with patch("app.services.llm_classifier.classify_with_groq", side_effect=Exception("Groq Service Unavailable")):
        res_3 = detect_root_cause(pay_3)
    print("\n--- TEST 3: Groq Unavailable (Fallback Test) ---")
    print(f"Payment ID: {pay_3.payment_id}")
    print(f"Diagnosed Root Cause: {res_3.root_cause.value}")
    print(f"Confidence: {res_3.confidence}")
    print(f"Source: {res_3.source}")
    print(f"Reasoning: {res_3.reasoning.encode('ascii', 'replace').decode('ascii')}")

    assert res_3.root_cause == RootCause.UNKNOWN
    assert res_3.source == "deterministic_fallback"
    assert res_3.confidence is None
    print(">> [PASS] Test 3: Failure gracefully fell back to RootCause.UNKNOWN and deterministic containment.")

    # -------------------------------------------------------------
    # Test 4: Full Batch Execution & Breakdown Reporting
    # -------------------------------------------------------------
    clear_cache()
    db = SessionLocal()
    try:
        print("\n--- TEST 4: Full Batch Run (50 Payments) ---")
        batch = generate_failed_payments(db, count=50)
        result = run_batch_recovery(db, batch.batch_id)
        
        # Count sources from payments in this batch
        payments = db.query(Payment).filter(Payment.batch_id == batch.batch_id).all()
        
        rules_count = 0
        groq_count = 0
        cache_count = 0
        fallback_count = 0
        
        for p in payments:
            # Check diagnose audit log
            from app.models import AuditLog
            audit = db.query(AuditLog).filter(AuditLog.payment_id == p.payment_id, AuditLog.stage == "diagnose").first()
            if audit:
                reasoning = audit.reasoning
                if "[Source: groq]" in reasoning:
                    groq_count += 1
                elif "[Source: cache]" in reasoning:
                    cache_count += 1
                elif "[Source: deterministic_fallback]" in reasoning:
                    fallback_count += 1
                else:
                    rules_count += 1
        
        print("\n================ BATCH EXECUTION RESULTS ================")
        print(f"Batch ID: {batch.batch_id}")
        print(f"Total Payments: {len(payments)}")
        print(f"Recovered Count: {result['recovered']}")
        print(f"Recovery Rate: {result['recovery_rate']*100:.1f}%")
        print("---------------------------------------------------------")
        print(f"Deterministic Rules: {rules_count}")
        print(f"Diagnosis Cache Hits: {cache_count}")
        print(f"Groq AI Escalations: {groq_count}")
        print(f"Deterministic Fallback: {fallback_count}")
        print(f"Total Diagnoses Reconciled: {rules_count + cache_count + groq_count + fallback_count} == {len(payments)}")
        print("=========================================================")
        
        assert rules_count + cache_count + groq_count + fallback_count == len(payments)
        print(">> [PASS] Test 4: Full batch executed and 100% reconciled.")

    finally:
        db.close()

    print("\n================================================================")
    print("ALL 4 SUBMISSION VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("================================================================")

if __name__ == "__main__":
    run_all_tests()
