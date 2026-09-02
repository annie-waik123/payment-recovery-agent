from typing import List, Optional
from collections import Counter
import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()


from app.database import engine, Base, SessionLocal
from app.models import BatchRun, Payment, Intervention, AuditLog, PaymentStatus, RootCause, InterventionType
from app.seed_data import generate_failed_payments
from app.services.classifier import classify_batch
from app.services.guardrails import guard_batch
from app.services.policy import decide_batch
from app.services.orchestrator import run_batch_recovery
from app.schemas import (
    BatchRunSchema,
    PaymentSchema,
    PaymentDetailSchema,
    AuditLogSchema,
    MetricsResponse,
)


app = FastAPI(
    title="Payment Recovery Agent"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# Step 7: New REST endpoints

@app.post("/batches", response_model=BatchRunSchema)
def create_batch(count: int = 50):
    """Create a batch and seed count failed payments."""
    db = SessionLocal()
    try:
        batch = generate_failed_payments(db, count)
        return batch
    finally:
        db.close()


@app.post("/batches/{batch_id}/run")
def run_batch(batch_id: str):
    """Run recovery workflow for the specified batch."""
    db = SessionLocal()
    try:
        batch = db.query(BatchRun).filter(BatchRun.batch_id == batch_id).first()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        result = run_batch_recovery(db, batch_id)
        return result
    finally:
        db.close()


@app.get("/batches/{batch_id}", response_model=BatchRunSchema)
def get_batch(batch_id: str):
    """Retrieve summary metadata for a single batch run."""
    db = SessionLocal()
    try:
        batch = db.query(BatchRun).filter(BatchRun.batch_id == batch_id).first()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        return batch
    finally:
        db.close()


@app.get("/batches", response_model=List[BatchRunSchema])
def list_batches():
    """List all batch runs, sorted by start time descending."""
    db = SessionLocal()
    try:
        batches = db.query(BatchRun).order_by(BatchRun.started_at.desc()).all()
        return batches
    finally:
        db.close()


@app.get("/payments", response_model=List[PaymentSchema])
def list_payments(
    batch_id: Optional[str] = Query(None, description="Filter payments by batch_id"),
    status: Optional[str] = Query(None, description="Filter payments by status")
):
    """Query payments with optional batch_id and status filters."""
    db = SessionLocal()
    try:
        query = db.query(Payment)
        if batch_id:
            query = query.filter(Payment.batch_id == batch_id)
        if status:
            query = query.filter(Payment.status == status)
        return query.all()
    finally:
        db.close()


@app.get("/payments/{payment_id}", response_model=PaymentDetailSchema)
def get_payment(payment_id: str):
    """Retrieve a single payment with its detailed intervention history."""
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        interventions = (
            db.query(Intervention)
            .filter(Intervention.payment_id == payment_id)
            .order_by(Intervention.executed_at.asc())
            .all()
        )
        payment.interventions = interventions
        return payment
    finally:
        db.close()


@app.get("/audit", response_model=List[AuditLogSchema])
def get_audit_trail(
    payment_id: Optional[str] = Query(None, description="Filter audit logs by payment_id"),
    batch_id: Optional[str] = Query(None, description="Filter audit logs by batch_id")
):
    """Query audit logs, optionally filtered by payment_id or batch_id."""
    db = SessionLocal()
    try:
        query = db.query(AuditLog)
        if payment_id:
            query = query.filter(AuditLog.payment_id == payment_id)
        if batch_id:
            query = query.join(Payment).filter(Payment.batch_id == batch_id)
        return query.order_by(AuditLog.timestamp.asc()).all()
    finally:
        db.close()


@app.get("/metrics/{batch_id}", response_model=MetricsResponse)
def get_batch_metrics(batch_id: str):
    """Return metrics for the selected batch, including breakdowns."""
    db = SessionLocal()
    try:
        batch = db.query(BatchRun).filter(BatchRun.batch_id == batch_id).first()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")

        payments = db.query(Payment).filter(Payment.batch_id == batch_id).all()
                # Revenue impact — "at risk" is the total amount across every
        # payment in the batch (all of it entered the recovery pipeline
        # as a failure); "recovered" is the portion actually won back.
        revenue_at_risk_paise = sum(p.amount for p in payments)
        revenue_recovered_paise = sum(
            p.amount for p in payments if p.status == PaymentStatus.RECOVERED
        )

        # Root cause breakdown
        causes = [p.root_cause.value for p in payments if p.root_cause is not None]
        cause_counts = dict(Counter(causes))
        for rc in RootCause:
            if rc.value not in cause_counts:
                cause_counts[rc.value] = 0

        # Intervention breakdown (latest intervention type for each payment in this batch)
        interventions = (
            db.query(Intervention)
            .join(Payment)
            .filter(Payment.batch_id == batch_id)
            .all()
        )
        latest_interventions = {}
        for iv in interventions:
            pid = iv.payment_id
            if pid not in latest_interventions or iv.executed_at > latest_interventions[pid].executed_at:
                latest_interventions[pid] = iv

        itypes = [iv.type.value for iv in latest_interventions.values()]
        itype_counts = dict(Counter(itypes))
        for it in InterventionType:
            if it.value not in itype_counts:
                itype_counts[it.value] = 0

            return MetricsResponse(
            batch_id=batch_id,
            total_payments=batch.total,
            recovery_rate=batch.recovery_rate,
            recovered_count=batch.recovered,
            unrecoverable_count=batch.unrecoverable,
            root_cause_breakdown=cause_counts,
            intervention_breakdown=itype_counts,
            revenue_at_risk_paise=revenue_at_risk_paise,
            revenue_recovered_paise=revenue_recovered_paise,
        )
    finally:
        db.close()
