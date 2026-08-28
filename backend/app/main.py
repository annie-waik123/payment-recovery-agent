from fastapi import FastAPI, HTTPException

from app.database import engine, Base, SessionLocal
from app.models import BatchRun, Payment, Intervention, AuditLog  # noqa: F401
from app.seed_data import generate_failed_payments
from app.services.classifier import classify_batch
from app.services.guardrails import guard_batch
from app.services.policy import decide_batch

app = FastAPI(
    title="Payment Recovery Agent"
)

Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {
        "message": "Payment Recovery Agent running"
    }


@app.post("/batch/seed")
def seed_batch(count: int = 50):
    db = SessionLocal()
    try:
        batch = generate_failed_payments(db, count)
        return {
            "message": f"{count} failed payments generated",
            "batch_id": batch.batch_id,
            "total": batch.total,
            "recovered": batch.recovered,
            "unrecoverable": batch.unrecoverable,
            "recovery_rate": batch.recovery_rate,
        }
    finally:
        db.close()


@app.post("/batches/{batch_id}/classify")
def classify_batch_endpoint(batch_id: str):
    db = SessionLocal()
    try:
        batch = db.query(BatchRun).filter(BatchRun.batch_id == batch_id).first()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")

        total, breakdown = classify_batch(db, batch_id)
        return {
            "batch_id": batch_id,
            "total_classified": total,
            "root_cause_breakdown": breakdown,
        }
    finally:
        db.close()


@app.post("/batches/{batch_id}/decide")
def decide_batch_endpoint(batch_id: str):
    db = SessionLocal()
    try:
        batch = db.query(BatchRun).filter(BatchRun.batch_id == batch_id).first()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")

        total, breakdown = decide_batch(db, batch_id)
        return {
            "batch_id": batch_id,
            "total_decisions": total,
            "intervention_breakdown": breakdown,
        }
    finally:
        db.close()


@app.post("/batches/{batch_id}/guardrails")
def guard_batch_endpoint(batch_id: str):
    db = SessionLocal()
    try:
        batch = db.query(BatchRun).filter(BatchRun.batch_id == batch_id).first()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")

        result = guard_batch(db, batch_id)
        return {
            "batch_id": batch_id,
            **result,
        }
    finally:
        db.close()
