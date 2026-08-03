"""Safety Layer — 6 sequential checks on every LLM response before formatting."""
from __future__ import annotations
import re
import structlog
from ai.orchestrator.state import OrchestratorState
from ai.security.pii_masker import mask_pii_in_text
from ai.security.injection_detector import detect_injection

logger = structlog.get_logger()

_SAFE_FALLBACK = "I'm sorry, I cannot provide a response to that request. Please consult a qualified financial advisor."
_SEBI_DISCLAIMER = "\n\n⚠️ Disclaimer: This is not financial advice. Please consult a SEBI-registered investment adviser."

# Toxicity classification — lazy loaded
_TOXICITY_PIPELINE = None

def _get_toxicity_classifier():
    global _TOXICITY_PIPELINE
    if _TOXICITY_PIPELINE is None:
        from transformers import pipeline  # type: ignore
        _TOXICITY_PIPELINE = pipeline("text-classification", model="unitary/toxic-bert", top_k=None)
    return _TOXICITY_PIPELINE

def _check_toxicity(text: str) -> float:
    """Return toxicity score [0,1]. Returns 0.0 on model error."""
    try:
        classifier = _get_toxicity_classifier()
        results = classifier(text[:512])  # truncate for speed
        # results is list of lists of {label, score}
        flat = results[0] if isinstance(results[0], list) else results
        for item in flat:
            if item["label"].lower() in ("toxic", "1"):
                return float(item["score"])
        return 0.0
    except Exception:
        return 0.0

_NUMERICAL_CLAIM_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?%.*?\b(?:return|earn|grow|yield|gain)\b"
    r"|\b(?:return|earn|grow|yield|gain)\b.*?\b\d+(?:\.\d+)?%",
    re.I,
)

async def safety_layer_node(state: OrchestratorState) -> dict:
    message = state.get("llm_response") or ""
    llm_confidence = state.get("llm_confidence", 0.0)
    rag_result = state.get("rag_result")
    portfolio_result = state.get("portfolio_result")

    metadata_updates: dict = {}

    # Check 1: Prompt injection scan on LLM output
    if detect_injection(message):
        logger.warning("safety_layer_injection_in_llm_output")
        message = _SAFE_FALLBACK
        return {"safe_response": {"message": message, "citations": [], "metadata": metadata_updates}}

    # Check 2: PII scan + masking
    message = mask_pii_in_text(message)

    # Check 3: Toxicity classification
    toxicity_score = _check_toxicity(message)
    if toxicity_score > 0.7:
        logger.warning("safety_layer_toxicity_exceeded", score=toxicity_score)
        message = _SAFE_FALLBACK

    # Check 4: Low confidence warning
    if llm_confidence < 0.4:
        metadata_updates["low_confidence_warning"] = (
            f"AI confidence is low ({llm_confidence:.2f}). Please verify this information."
        )

    # Check 5: Numerical disclaimer
    if _NUMERICAL_CLAIM_PATTERN.search(message) and not portfolio_result:
        message = message + _SEBI_DISCLAIMER

    # Check 6: Citation enforcement
    citations = state.get("composed_response", {}).get("citations", []) if state.get("composed_response") else []
    if rag_result and not citations:
        # Trigger one retry of RAG
        try:
            from ai.rag.retrieval import retrieve
            retry_results = await retrieve(state.get("raw_query", ""), top_k=5)
            citations = [c.model_dump() for c in retry_results] if retry_results else []
            if not citations:
                logger.warning("safety_layer_rag_retry_no_results")
                message = message + "\n\n[Note: Regulatory sources could not be retrieved for this response.]"
        except Exception:
            pass

    return {
        "safe_response": {
            "message": message,
            "citations": citations,
            "metadata": metadata_updates,
        }
    }
