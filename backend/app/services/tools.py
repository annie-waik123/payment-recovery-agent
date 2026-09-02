"""Deterministic mock tools for tool-augmented diagnosis in RecoveryMind AI.

Zero external APIs, pure deterministic offline data for predictable audits and demos.
"""

from typing import Any, Dict, Optional
from app.models import Payment

BANK_HEALTH_REGISTRY: Dict[str, Dict[str, Any]] = {
    "HDFC": {
        "bank": "HDFC",
        "status": "degraded",
        "success_rate": 0.45,
        "latency_ms": 1450,
        "incident": "High latency and intermittent drops on UPI/Netbanking gateway",
    },
    "SBI": {
        "bank": "SBI",
        "status": "degraded",
        "success_rate": 0.38,
        "latency_ms": 2200,
        "incident": "Core banking switch timeout during high volume",
    },
    "ICICI": {
        "bank": "ICICI",
        "status": "healthy",
        "success_rate": 0.98,
        "latency_ms": 180,
        "incident": None,
    },
    "AXIS": {
        "bank": "AXIS",
        "status": "healthy",
        "success_rate": 0.96,
        "latency_ms": 210,
        "incident": None,
    },
    "KOTAK": {
        "bank": "KOTAK",
        "status": "healthy",
        "success_rate": 0.97,
        "latency_ms": 190,
        "incident": None,
    },
    "DEFAULT": {
        "bank": "Generic Gateway",
        "status": "healthy",
        "success_rate": 0.95,
        "latency_ms": 200,
        "incident": None,
    },
}


def get_bank_health(bank_name: Optional[str] = None) -> Dict[str, Any]:
    """Deterministic lookup of bank health status."""
    if not bank_name:
        return BANK_HEALTH_REGISTRY["DEFAULT"]
    
    key = bank_name.strip().upper()
    for bank_key, data in BANK_HEALTH_REGISTRY.items():
        if bank_key in key:
            return data
    return {
        "bank": bank_name,
        "status": "healthy",
        "success_rate": 0.95,
        "latency_ms": 200,
        "incident": None,
    }


def get_bank_health_for_payment(payment: Payment) -> Dict[str, Any]:
    """Deterministically resolves bank health context for a failed payment.
    
    Infers the bank from payment method/error details or payment ID hash
    to provide rich context for Groq AI forensic diagnosis.

    """
    reason = (payment.error_reason or "").lower()
    method = (payment.method or "").lower()
    
    # Deterministic mapping based on payment characteristics
    if "hdfc" in reason:
        return get_bank_health("HDFC")
    if "sbi" in reason:
        return get_bank_health("SBI")
    if "icici" in reason:
        return get_bank_health("ICICI")
    
    # For netbanking/card/upi failures with generic errors, deterministically map by payment_id
    if method in {"netbanking", "upi", "card"}:
        hash_val = sum(ord(c) for c in (payment.payment_id or "0")) % 4
        banks = ["HDFC", "SBI", "ICICI", "AXIS"]
        return get_bank_health(banks[hash_val])
        
    return get_bank_health("DEFAULT")
