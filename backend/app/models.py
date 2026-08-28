import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Enum,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _id() -> str:
    return uuid.uuid4().hex[:12]


class PaymentStatus(str, enum.Enum):
    FAILED = "failed"
    RETRYING = "retrying"
    RECOVERED = "recovered"
    UNRECOVERABLE = "unrecoverable"


class RootCause(str, enum.Enum):
    INSUFFICIENT_FUNDS = "insufficient_funds"
    ISSUER_DECLINE = "issuer_decline"
    NETWORK_TIMEOUT = "network_timeout"
    EXPIRED_CARD = "expired_card"
    RISK_BLOCK = "risk_block"
    UNKNOWN = "unknown"


class InterventionType(str, enum.Enum):
    RETRY_NOW = "retry_now"
    RETRY_LATER = "retry_later"
    SUGGEST_ALT_METHOD = "suggest_alt_method"
    HOLD = "hold"
    UNRECOVERABLE = "unrecoverable"


class BatchRun(Base):
    __tablename__ = "batch_runs"

    batch_id = Column(String, primary_key=True, default=_id)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    total = Column(Integer, default=0)
    recovered = Column(Integer, default=0)
    unrecoverable = Column(Integer, default=0)
    recovery_rate = Column(Float, default=0.0)

    payments = relationship("Payment", back_populates="batch")


class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String, primary_key=True, default=_id)
    batch_id = Column(String, ForeignKey("batch_runs.batch_id"), nullable=False)
    order_id = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)  # paise
    currency = Column(String, default="INR")
    method = Column(String, nullable=False)
    error_code = Column(String, nullable=False)
    error_reason = Column(Text, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.FAILED)
    root_cause = Column(Enum(RootCause), nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    batch = relationship("BatchRun", back_populates="payments")
    interventions = relationship("Intervention", back_populates="payment")
    audit_entries = relationship("AuditLog", back_populates="payment")


class Intervention(Base):
    __tablename__ = "interventions"

    intervention_id = Column(String, primary_key=True, default=_id)
    payment_id = Column(String, ForeignKey("payments.payment_id"), nullable=False)
    type = Column(Enum(InterventionType), nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow)
    outcome = Column(String, nullable=True)  # recovered | still_failing | held | flagged
    razorpay_ref = Column(String, nullable=True)  # null while mocked

    payment = relationship("Payment", back_populates="interventions")


class AuditLog(Base):
    __tablename__ = "audit_log"

    entry_id = Column(String, primary_key=True, default=_id)
    payment_id = Column(String, ForeignKey("payments.payment_id"), nullable=False)
    stage = Column(String, nullable=False)  # detect|diagnose|decide|act|stop_check
    reasoning = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)  # only set on LLM-fallback path
    timestamp = Column(DateTime, default=datetime.utcnow)

    payment = relationship("Payment", back_populates="audit_entries")
