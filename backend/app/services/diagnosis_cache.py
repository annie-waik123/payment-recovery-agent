"""In-memory cache for AI-generated payment failure diagnoses.

Prevents redundant LLM calls when identical unclassified failure patterns
recur across a batch or multiple transactions.

Guarantees:
- Only caches AI diagnoses (Groq) for unclassified failures.
- Deterministic rules bypass cache and are never stored here.

"""

from typing import Any, Dict, Optional
from app.models import Payment

# In-memory diagnosis cache
CACHE: Dict[str, Any] = {}
CACHE_STATS: Dict[str, int] = {"hits": 0, "misses": 0}


def get_cache_key(payment: Payment, bank_health: Optional[Dict[str, Any]] = None) -> str:
    """Generate a deterministic fingerprint for a payment failure pattern.

    Components:
    - error_code (normalized uppercase)
    - error_reason (normalized lowercase)
    - method (normalized lowercase)
    - bank_name & bank_status (if present)
    """
    code = (payment.error_code or "").strip().upper()
    reason = (payment.error_reason or "").strip().lower()
    method = (payment.method or "").strip().lower()

    bank_name = ""
    bank_status = ""
    if bank_health:
        bank_name = str(bank_health.get("bank", "")).strip().upper()
        bank_status = str(bank_health.get("status", "")).strip().lower()

    return f"{code}|{reason}|{method}|{bank_name}|{bank_status}"


def get_cached_diagnosis(key: str) -> Optional[Any]:
    """Retrieve diagnosis from cache if present, updating stats."""
    if key in CACHE:
        CACHE_STATS["hits"] += 1
        return CACHE[key]
    CACHE_STATS["misses"] += 1
    return None


def set_cached_diagnosis(key: str, diagnosis: Any) -> None:
    """Store an AI-generated diagnosis in the cache."""
    if diagnosis is not None:
        CACHE[key] = diagnosis


def clear_cache() -> None:
    """Clear in-memory cache and reset statistics."""
    CACHE.clear()
    CACHE_STATS["hits"] = 0
    CACHE_STATS["misses"] = 0


def get_cache_stats() -> Dict[str, int]:
    """Return cache hits, misses, and current item count."""
    return {
        "hits": CACHE_STATS["hits"],
        "misses": CACHE_STATS["misses"],
        "size": len(CACHE),
    }
