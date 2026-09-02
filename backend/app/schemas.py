from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict
from app.models import PaymentStatus, RootCause, InterventionType

class BatchRunSchema(BaseModel):
    batch_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    total: int
    recovered: int
    unrecoverable: int
    recovery_rate: float

    class Config:
        from_attributes = True

class InterventionSchema(BaseModel):
    intervention_id: str
    payment_id: str
    type: InterventionType
    executed_at: datetime
    outcome: Optional[str] = None
    razorpay_ref: Optional[str] = None

    class Config:
        from_attributes = True

class PaymentSchema(BaseModel):
    payment_id: str
    batch_id: str
    order_id: str
    amount: int
    currency: str
    method: str
    error_code: str
    error_reason: str
    status: PaymentStatus
    root_cause: Optional[RootCause] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PaymentDetailSchema(PaymentSchema):
    interventions: List[InterventionSchema] = []

class AuditLogSchema(BaseModel):
    entry_id: str
    payment_id: str
    stage: str
    reasoning: str
    confidence: Optional[float] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class MetricsResponse(BaseModel):
    batch_id: str
    total_payments: int
    recovery_rate: float
    recovered_count: int
    unrecoverable_count: int
    root_cause_breakdown: Dict[str, int]
    intervention_breakdown: Dict[str, int]
    revenue_at_risk_paise: int
    revenue_recovered_paise: int