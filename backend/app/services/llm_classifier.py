"""AI diagnostic escalation using Groq with in-memory caching.

Diagnostic hierarchy for unclassified residual failures:
1. Diagnosis Cache (in-memory fingerprint match) -> 'cache'
2. Primary AI: Groq (qwen/qwen3.8-27b via OpenAI-compatible endpoint) -> 'groq'
3. Deterministic Fallback (quarantine + guardrails hold) -> 'deterministic_fallback'

Design commitment:
- Rules remain primary (85% volume, 0 token cost).
- Only unknown residual failures reach this module.
- Diagnoses only, never decides money movement or interventions.
"""

import json
import logging
import os
from dotenv import load_dotenv

from pydantic import BaseModel, Field

from app.models import Payment, RootCause
from app.services.tools import get_bank_health_for_payment

# Ensure environment variables from .env are loaded
load_dotenv()

logger = logging.getLogger(__name__)

GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")


class AIDiagnosis(BaseModel):
    root_cause: str = Field(description="Must be one of the RootCause enum values.")
    confidence: float = Field(ge=0.0, le=1.0)
    forensic_reasoning: str = Field(description="1-2 sentence analysis of the failure pattern.")
    source: str = Field(default="groq", description="AI Provider source: 'groq' | 'cache'")


_SYSTEM_INSTRUCTION = """You are a payment failure diagnostic assistant for an Indian fintech platform. Your ONLY job is to determine WHY a payment failed. You do not decide what action to take -- a separate, deterministic policy engine handles that.

A rule-based classifier already checked this payment against known patterns and could not confidently match it. Give your own independent diagnosis. Be honest about uncertainty in your confidence score: 0.9+ only if the evidence is unambiguous, 0.5-0.7 if you're inferring from incomplete signals, below 0.5 if largely guessing."""


def classify_with_groq(
    payment: Payment, bank_health: dict | None = None
) -> AIDiagnosis | None:
    """Primary AI diagnosis via Groq (OpenAI-compatible endpoint). Returns None on any error."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set -- skipping AI escalation for %s", payment.payment_id)
        return None

    valid_causes = [c.value for c in RootCause if c != RootCause.UNKNOWN]
    if bank_health is None:
        bank_health = get_bank_health_for_payment(payment)
    bank_health_info = f"{bank_health['bank']} (Status: {bank_health['status']}, SR: {int(bank_health['success_rate']*100)}%, Latency: {bank_health.get('latency_ms', 200)}ms)"
    if bank_health.get("incident"):
        bank_health_info += f" - Incident: {bank_health['incident']}"

    prompt = f"""Analyze this Razorpay payment failure:
- Amount: {payment.amount} | Method: {payment.method}
- Error Code: {payment.error_code}
- Error Reason: {payment.error_reason}
- Retry count so far: {payment.retry_count or 0}
- Bank Health Telemetry: {bank_health_info}

Task: Choose exactly ONE root_cause from strictly this list: {valid_causes}
Provide 'forensic_reasoning' explaining why the payment failed.
Respond strictly in JSON format with keys: 'root_cause', 'confidence' (0.0 to 1.0), and 'forensic_reasoning'."""

    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            logger.warning("Empty Groq response for %s", payment.payment_id)
            return None

        data = json.loads(content)
        raw_cause = str(data.get("root_cause", "")).lower().strip()
        matched_cause = None
        for vc in valid_causes:
            if vc == raw_cause or vc in raw_cause:
                matched_cause = vc
                break

        if not matched_cause:
            logger.warning("Groq returned unrecognized root_cause '%s' for %s", raw_cause, payment.payment_id)
            return None

        confidence = float(data.get("confidence", 0.85))
        confidence = max(0.0, min(1.0, confidence))
        reasoning = str(data.get("forensic_reasoning", "Groq AI forensic diagnosis."))

        return AIDiagnosis(
            root_cause=matched_cause,
            confidence=confidence,
            forensic_reasoning=reasoning,
            source="groq",
        )

    except Exception as e:
        logger.warning(
            "Groq AI call failed for %s (%s: %s)",
            payment.payment_id,
            type(e).__name__,
            e,
        )
        return None


def classify_with_fallback(
    payment: Payment, bank_health: dict | None = None
) -> tuple[AIDiagnosis | None, str]:
    """Diagnostic hierarchy for unclassified failures:
    1. Diagnosis Cache (in-memory match) -> source: 'cache'
    2. Primary AI: Groq -> source: 'groq'
    3. Deterministic Fallback -> source: 'deterministic_fallback'
    """
    from app.services.diagnosis_cache import (
        get_cache_key,
        get_cached_diagnosis,
        set_cached_diagnosis,
    )

    if bank_health is None:
        bank_health = get_bank_health_for_payment(payment)

    cache_key = get_cache_key(payment, bank_health)

    # 1. Check Cache
    cached = get_cached_diagnosis(cache_key)
    if cached is not None:
        logger.info("Diagnosis cache HIT for payment %s (key: %s)", payment.payment_id, cache_key)
        return cached, "cache"

    # 2. Attempt Primary AI: Groq
    try:
        groq_result = classify_with_groq(payment, bank_health)
        if groq_result is not None:
            groq_result.source = "groq"
            set_cached_diagnosis(cache_key, groq_result)
            return groq_result, "groq"
    except Exception as e:
        logger.warning("Groq execution error for %s: %s", payment.payment_id, e)

    # 3. Final Deterministic Fallback
    logger.warning("AI provider failed for %s -- falling back to deterministic quarantine", payment.payment_id)
    return None, "deterministic_fallback"
