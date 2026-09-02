from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, engine, Base
from app.models import BatchRun, Payment, Intervention, AuditLog

client = TestClient(app)

def test_rest_endpoints():
    print("Initializing test database for API tests...")
    Base.metadata.create_all(bind=engine)

    print("Testing POST /batches (seeding)...")
    response = client.post("/batches?count=5")
    assert response.status_code == 200
    batch_data = response.json()
    batch_id = batch_data["batch_id"]
    print(f"Created batch: {batch_id}, Total: {batch_data['total']}")

    print("Testing GET /batches...")
    response = client.get("/batches")
    assert response.status_code == 200
    batches = response.json()
    assert len(batches) >= 1
    print(f"Batches list length: {len(batches)}")

    print("Testing GET /batches/{batch_id} (before run)...")
    response = client.get(f"/batches/{batch_id}")
    assert response.status_code == 200
    assert response.json()["finished_at"] is None

    print("Testing POST /batches/{batch_id}/run...")
    response = client.post(f"/batches/{batch_id}/run")
    assert response.status_code == 200
    run_result = response.json()
    print("Run completed:", run_result)
    assert run_result["recovery_rate"] >= 0.0
    assert run_result["finished_at"] is not None

    print("Testing GET /batches/{batch_id} (after run)...")
    response = client.get(f"/batches/{batch_id}")
    assert response.status_code == 200
    assert response.json()["finished_at"] is not None

    print("Testing GET /payments with batch filter...")
    response = client.get(f"/payments?batch_id={batch_id}")
    assert response.status_code == 200
    payments = response.json()
    assert len(payments) == 5
    first_payment_id = payments[0]["payment_id"]
    print(f"Fetched {len(payments)} payments. First payment ID: {first_payment_id}")

    print("Testing GET /payments/{payment_id}...")
    response = client.get(f"/payments/{first_payment_id}")
    assert response.status_code == 200
    payment_detail = response.json()
    assert "interventions" in payment_detail
    assert len(payment_detail["interventions"]) >= 1
    print(f"Payment {first_payment_id} has {len(payment_detail['interventions'])} interventions.")

    print("Testing GET /audit...")
    response = client.get(f"/audit?batch_id={batch_id}")
    assert response.status_code == 200
    audit_trail = response.json()
    assert len(audit_trail) >= 5 * 4  # 4 audit entries (diagnose, decide, stop_check, act) per payment
    print(f"Audit trail entries count: {len(audit_trail)}")

    print("Testing GET /metrics/{batch_id}...")
    response = client.get(f"/metrics/{batch_id}")
    assert response.status_code == 200
    metrics = response.json()
    print("Metrics response:", metrics)
    assert "recovery_rate" in metrics
    assert "root_cause_breakdown" in metrics
    assert "intervention_breakdown" in metrics
    assert "recovered_count" in metrics
    assert "unrecoverable_count" in metrics

    print("\nAPI Rest endpoints test passed successfully! All Step 7 endpoints operate correctly.")

if __name__ == "__main__":
    test_rest_endpoints()
