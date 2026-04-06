from __future__ import annotations

import datetime
import json
import math
import os
import threading
from pathlib import Path
from typing import Optional

import structlog

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# NaN / null helpers
# ---------------------------------------------------------------------------

def _str(val) -> str:
    """Return str(val), or '' for None/NaN floats."""
    if val is None:
        return ""
    if isinstance(val, float) and math.isnan(val):
        return ""
    return str(val)


def _is_null_val(val) -> bool:
    """True for None, NaN floats, and empty/whitespace-only strings."""
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


# ---------------------------------------------------------------------------
# Token / cost tracking  (thread-safe)
# ---------------------------------------------------------------------------

# DeepSeek pricing (per 1M tokens)
UNIT_COST = {
    "input_per_1m_usd": 0.14,
    "cached_input_per_1m_usd": 0.014,   # 10× cheaper for cache hits
    "output_per_1m_usd": 0.28,
}

TOKEN_LOG: dict = {
    "calls": 0,
    "input_tokens": 0,       # total prompt tokens (cache-hit + cache-miss)
    "output_tokens": 0,
    "cache_tokens": 0,        # subset of input_tokens served from cache
    "input_cost_usd": 0.0,
    "cached_cost_usd": 0.0,
    "output_cost_usd": 0.0,
    "total_cost_usd": 0.0,
}
_TOKEN_LOCK = threading.Lock()

_COST_CAP = 2.0            # hard stop


def get_token_log() -> dict:
    """Return a snapshot of the current run's token counters."""
    with _TOKEN_LOCK:
        snap = dict(TOKEN_LOG)
    snap["unit_cost"] = dict(UNIT_COST)
    return snap


def reset_token_log() -> None:
    """Reset TOKEN_LOG to zero for a fresh pipeline run."""
    with _TOKEN_LOCK:
        TOKEN_LOG["calls"] = 0
        TOKEN_LOG["input_tokens"] = 0
        TOKEN_LOG["output_tokens"] = 0
        TOKEN_LOG["cache_tokens"] = 0
        TOKEN_LOG["input_cost_usd"] = 0.0
        TOKEN_LOG["cached_cost_usd"] = 0.0
        TOKEN_LOG["output_cost_usd"] = 0.0
        TOKEN_LOG["total_cost_usd"] = 0.0


_TOKEN_LOG_PATH = Path(__file__).parent.parent / "data" / "token_logs.json"


def save_token_log() -> None:
    """Append the current run's token snapshot (with timestamp) to data/token_logs.json."""
    record = get_token_log()
    record["timestamp"] = datetime.datetime.now().isoformat(timespec="seconds")

    # Read existing records (or start fresh)
    if _TOKEN_LOG_PATH.exists():
        try:
            existing: list = json.loads(_TOKEN_LOG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            existing = []
    else:
        existing = []

    existing.append(record)
    _TOKEN_LOG_PATH.write_text(json.dumps(existing, indent=2))
    log.info("token_log_saved", path=str(_TOKEN_LOG_PATH), runs=len(existing))


# ---------------------------------------------------------------------------
# Lazy LM initialisation (so tests can import without an API key)
# ---------------------------------------------------------------------------
_lm = None
_enricher = None
_LM_LOCK = threading.Lock()


def _ensure_lm():
    global _lm, _enricher
    if _lm is not None:
        return

    with _LM_LOCK:
        if _lm is not None:  # double-checked locking
            return

        import dspy

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")

        _lm = dspy.LM(
            model="openai/deepseek-chat",
            api_key=api_key,
            api_base="https://api.deepseek.com",
            max_tokens=800,
            cache=False,   # disable disk cache so every run makes real API calls
        )
        dspy.configure(lm=_lm)
        _enricher = dspy.ChainOfThought(ProductEnricher)
        log.info("lm_init", model="openai/deepseek-chat", max_tokens=800)


# ---------------------------------------------------------------------------
# DSPy Signature
# ---------------------------------------------------------------------------
def _build_signature():
    import dspy

    class ProductEnricher(dspy.Signature):
        """Extract structured food product attributes. Only use common food categories.
        Output allergens and dietary_flags as comma-separated strings.
        If unknown output empty string. Confidence is 0-1."""

        product_name: str = dspy.InputField()
        raw_categories: str = dspy.InputField()
        raw_ingredients: str = dspy.InputField()
        raw_allergens: str = dspy.InputField()

        categories_clean: str = dspy.OutputField()
        allergens_extracted: str = dspy.OutputField()
        dietary_flags: str = dspy.OutputField()
        quantity_normalized: str = dspy.OutputField()
        confidence: float = dspy.OutputField()

    return ProductEnricher


# Defined at module level once dspy is imported
try:
    import dspy as _dspy_check  # noqa: F401
    ProductEnricher = _build_signature()
except ImportError:
    ProductEnricher = None  # type: ignore




def _update_token_log(usage) -> None:
    """Update TOKEN_LOG from a LiteLLM/DSPy usage object (thread-safe)."""
    try:
        inp = getattr(usage, "prompt_tokens", 0) or 0
        out = getattr(usage, "completion_tokens", 0) or 0

        # Extract cache-hit tokens (OpenAI/DeepSeek: usage.prompt_tokens_details.cached_tokens)
        details = getattr(usage, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", 0) or 0
        non_cached = inp - cached

        input_cost  = (non_cached / 1_000_000) * UNIT_COST["input_per_1m_usd"]
        cached_cost = (cached    / 1_000_000) * UNIT_COST["cached_input_per_1m_usd"]
        output_cost = (out       / 1_000_000) * UNIT_COST["output_per_1m_usd"]
        call_cost   = input_cost + cached_cost + output_cost

        with _TOKEN_LOCK:
            TOKEN_LOG["calls"] += 1
            TOKEN_LOG["input_tokens"] += inp
            TOKEN_LOG["output_tokens"] += out
            TOKEN_LOG["cache_tokens"] += cached
            TOKEN_LOG["input_cost_usd"] += input_cost
            TOKEN_LOG["cached_cost_usd"] += cached_cost
            TOKEN_LOG["output_cost_usd"] += output_cost
            TOKEN_LOG["total_cost_usd"] += call_cost
            total_cost = TOKEN_LOG["total_cost_usd"]

        log.info(
            "llm_call_success",
            input_tokens=inp,
            cache_tokens=cached,
            output_tokens=out,
            call_cost_usd=round(call_cost, 6),
            total_cost_usd=round(total_cost, 4),
        )

        if total_cost > _COST_CAP:
            raise RuntimeError(f"Cost cap reached: ${total_cost:.4f} > ${_COST_CAP}")
    except RuntimeError:
        raise
    except Exception:
        pass  # token tracking is best-effort


def _call_llm(row: dict, attempt: int = 0) -> dict:
    """Call DSPy enricher and return validated output dict. Raises on failure."""
    import dspy
    from src.schema import DSPyOutput

    _ensure_lm()
    log.debug("llm_call_attempt", attempt=attempt + 1)

    pred = _enricher(
        product_name=_str(row.get("product_name")),
        raw_categories=_str(row.get("categories_en")),
        raw_ingredients=_str(row.get("ingredients_text_en")),
        raw_allergens=_str(row.get("allergens_en")),
    )

    # Extract token usage from dspy history
    try:
        history = dspy.settings.lm.history
        if history:
            last = history[-1]
            usage = getattr(last.get("response", None), "usage", None)
            if usage:
                _update_token_log(usage)
    except RuntimeError:
        raise
    except Exception:
        pass

    # Parse confidence
    raw_confidence = pred.confidence
    if isinstance(raw_confidence, str):
        try:
            raw_confidence = float(raw_confidence)
        except ValueError:
            raw_confidence = 0.0

    validated = DSPyOutput(
        categories_clean=pred.categories_clean or "",
        allergens_extracted=pred.allergens_extracted or "",
        dietary_flags=pred.dietary_flags or "",
        quantity_normalized=pred.quantity_normalized or "",
        confidence=raw_confidence,
    )
    return validated.model_dump()


def enrich_row(row: dict) -> tuple[dict, list[str], bool]:
    """Enrich a single row dict using rules + optional DSPy LLM call.

    Returns (enriched_dict, transformations_applied, llm_called).
    """
    enriched = dict(row)
    transformations: list[str] = []
    llm_called = False

    # Map rule-based cleaned fields to enriched field names
    enriched.setdefault("quantity_normalized", enriched.pop("quantity", None))
    enriched.setdefault("categories_clean", enriched.get("categories_en"))
    allergens_raw = _str(enriched.get("allergens_en"))
    enriched.setdefault(
        "allergens_extracted",
        [a.strip() for a in allergens_raw.split(",") if a.strip()],
    )
    labels_raw = _str(enriched.get("labels_en"))
    enriched.setdefault(
        "dietary_flags",
        [f.strip() for f in labels_raw.split(",") if f.strip()],
    )

    # Check if LLM call is warranted — check raw fields only, before any enrichment
    raw_null_fields = [
        f for f in ["categories_en", "allergens_en", "labels_en", "ingredients_text_en"]
        if not row.get(f)  # catches None, "", and missing keys
    ]
    should_call_llm = len(raw_null_fields) >= 1
    if not should_call_llm:
        log.debug("llm_call_skipped", reason="low_null_count", null_count=0)
        return enriched, transformations, False

    # Attempt LLM call with 1 retry
    llm_result: Optional[dict] = None
    for attempt in range(2):
        try:
            llm_result = _call_llm(row, attempt=attempt)
            break
        except RuntimeError as e:
            if "Cost cap" in str(e):
                raise
            log.warning("llm_attempt_failed", attempt=attempt + 1, error=str(e))
        except Exception as e:
            log.warning("llm_attempt_error", attempt=attempt + 1, error=str(e))

    if llm_result is None:
        log.debug("llm_call_skipped", reason="exception")
        return enriched, transformations, False

    # Apply only if confidence >= 0.5
    confidence = llm_result.get("confidence", 0.0)
    if confidence < 0.5:
        log.warning("llm_call_skipped", reason="low_confidence", confidence=confidence)
        return enriched, transformations, False

    llm_called = True

    if llm_result["categories_clean"] and not row.get("categories_en"):
        enriched["categories_clean"] = llm_result["categories_clean"]
        transformations.append(f"categories_clean: filled by LLM → '{llm_result['categories_clean']}'")
        log.info("llm_writeback", field="categories_clean", value=llm_result["categories_clean"])

    if llm_result["allergens_extracted"]:
        parsed = [a.strip() for a in llm_result["allergens_extracted"].split(",") if a.strip()]
        if parsed and not row.get("allergens_en"):
            enriched["allergens_extracted"] = parsed
            transformations.append(f"allergens_extracted: filled by LLM → {parsed}")
            log.info("llm_writeback", field="allergens_extracted", value=parsed)

    if llm_result["dietary_flags"]:
        parsed_flags = [f.strip() for f in llm_result["dietary_flags"].split(",") if f.strip()]
        if parsed_flags and not row.get("labels_en"):
            enriched["dietary_flags"] = parsed_flags
            transformations.append(f"dietary_flags: filled by LLM → {parsed_flags}")
            log.info("llm_writeback", field="dietary_flags", value=parsed_flags)

    if llm_result["quantity_normalized"] and not enriched.get("quantity_normalized"):
        enriched["quantity_normalized"] = llm_result["quantity_normalized"]
        transformations.append(
            f"quantity_normalized: filled by LLM → '{llm_result['quantity_normalized']}'"
        )

    return enriched, transformations, llm_called
