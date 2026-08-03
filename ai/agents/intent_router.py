"""Intent Router — LangGraph node that classifies incoming queries into one of
13 supported financial intents using sentence-embedding cosine similarity.

Startup behaviour
-----------------
1. Try to load pre-computed centroids from ``ai/agents/intent_centroids.json``.
2. On first run (file absent) embed the seed sentences with all-MiniLM-L6-v2,
   compute per-intent mean vectors, persist them to the JSON file, then keep
   them in ``INTENT_CENTROIDS``.

Classification logic
--------------------
* Embed the incoming query.
* Compute cosine similarity against every intent centroid.
* Collect all intents with similarity ≥ 0.5.
* If none qualify, fall back to ``intent="Banking"`` with the max observed score.
* Primary intent = highest-similarity qualifying intent.

SLA: ≤ 2 seconds enforced via ``asyncio.wait_for(..., timeout=2.0)``.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from ai.orchestrator.retry import retryable_node
from ai.orchestrator.state import OrchestratorState

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_INTENTS: list[str] = [
    "Portfolio_Review",
    "Portfolio_Rebalancing",
    "Transaction_Analysis",
    "Budgeting",
    "Savings",
    "Goal_Planning",
    "Investment_Education",
    "Taxation",
    "Banking",
    "Insurance",
    "Pension",
    "Market_News",
    "Account_Summary",
]

# Each intent maps to the service nodes that must be invoked.
INTENT_SERVICE_MAP: dict[str, list[str]] = {
    "Portfolio_Review":       ["portfolio", "financial_advisor"],
    "Portfolio_Rebalancing":  ["portfolio", "financial_advisor"],
    "Transaction_Analysis":   ["transaction_analytics", "financial_advisor"],
    "Budgeting":              ["transaction_analytics", "financial_advisor"],
    "Savings":                ["transaction_analytics", "financial_advisor"],
    "Goal_Planning":          ["financial_advisor"],
    "Investment_Education":   ["financial_advisor", "rag"],
    "Taxation":               ["financial_advisor", "rag"],
    "Banking":                ["financial_advisor"],
    "Insurance":              ["financial_advisor", "rag"],
    "Pension":                ["financial_advisor", "rag"],
    "Market_News":            ["financial_advisor", "rag"],
    "Account_Summary":        ["transaction_analytics", "financial_advisor"],
}

# Representative seed sentences (3-5 per intent) used to build centroids.
INTENT_SEED_SENTENCES: dict[str, list[str]] = {
    "Portfolio_Review": [
        "What should I do with my portfolio?",
        "Can you review my current investments?",
        "How is my portfolio performing?",
        "Give me an overview of my holdings",
        "Assess my investment portfolio",
    ],
    "Portfolio_Rebalancing": [
        "How should I rebalance my portfolio?",
        "My portfolio allocation is off, how do I fix it?",
        "Suggest rebalancing my investments",
        "What changes should I make to rebalance?",
        "Adjust my portfolio weights",
    ],
    "Transaction_Analysis": [
        "Analyse my spending this month",
        "Show me my recent transactions",
        "What did I spend money on last month?",
        "Break down my transaction history",
        "Analyse where my money went",
    ],
    "Budgeting": [
        "Help me create a budget",
        "How can I stick to a budget?",
        "I need help managing my monthly expenses",
        "Suggest a budget plan for me",
        "How do I control my spending?",
    ],
    "Savings": [
        "How much should I save every month?",
        "What is a good savings strategy?",
        "Help me save more money",
        "Suggest savings tips for me",
        "How can I build an emergency fund?",
    ],
    "Goal_Planning": [
        "Help me plan for retirement",
        "I want to save for a house, how do I plan?",
        "Set a financial goal for me",
        "How do I achieve my financial goals?",
        "Create a financial plan for buying a car",
    ],
    "Investment_Education": [
        "Explain what a mutual fund is",
        "Teach me about SIP investments",
        "What is a demat account?",
        "How does the stock market work?",
        "What are the risks of equity investments?",
    ],
    "Taxation": [
        "How much tax do I owe?",
        "Explain income tax slabs in India",
        "How can I save tax on my investments?",
        "What is Section 80C deduction?",
        "Help me with my tax planning",
    ],
    "Banking": [
        "What is the interest rate on my savings account?",
        "How do I open a fixed deposit?",
        "Tell me about Punjab and Sind Bank services",
        "What are the charges for NEFT transfers?",
        "How do I update my KYC?",
    ],
    "Insurance": [
        "Which insurance plan should I buy?",
        "Explain term life insurance",
        "What is ULIP and is it good?",
        "Help me choose a health insurance policy",
        "What does IRDAI regulate?",
    ],
    "Pension": [
        "Explain the National Pension System",
        "How do I register for NPS?",
        "What are the benefits of NPS tier 1 vs tier 2?",
        "Help me plan for my pension",
        "What is EPF and PPF?",
    ],
    "Market_News": [
        "What is happening in the stock market today?",
        "Latest news about Nifty 50",
        "How are markets performing this week?",
        "Tell me about recent RBI policy changes",
        "What are the latest SEBI regulations?",
    ],
    "Account_Summary": [
        "Give me a summary of my account",
        "What is my current account balance?",
        "Show me my account overview",
        "Summarise my financial account",
        "What transactions are pending in my account?",
    ],
}

# ---------------------------------------------------------------------------
# Centroid persistence path
# ---------------------------------------------------------------------------

_CENTROIDS_PATH = Path(__file__).parent / "intent_centroids.json"

# ---------------------------------------------------------------------------
# Lazy model + centroid initialisation
# ---------------------------------------------------------------------------
# We import sentence_transformers lazily inside _ensure_model() so that the
# module can be imported in test environments where a real model is patched
# before the first call.

_MODEL: Any = None
INTENT_CENTROIDS: dict[str, np.ndarray] = {}


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Return cosine similarity between two 1-D numpy arrays."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _ensure_model() -> Any:
    """Load the sentence-transformer model (once) and return it."""
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def _build_centroids(model: Any) -> dict[str, np.ndarray]:
    """Embed seed sentences and compute per-intent centroid vectors."""
    centroids: dict[str, np.ndarray] = {}
    for intent, sentences in INTENT_SEED_SENTENCES.items():
        embeddings = model.encode(sentences, convert_to_numpy=True)
        centroids[intent] = embeddings.mean(axis=0)
    return centroids


def _save_centroids(centroids: dict[str, np.ndarray]) -> None:
    """Serialise centroids to JSON (list of floats per intent)."""
    payload = {intent: vec.tolist() for intent, vec in centroids.items()}
    _CENTROIDS_PATH.write_text(json.dumps(payload), encoding="utf-8")


def _load_centroids() -> dict[str, np.ndarray] | None:
    """Try to load centroids from JSON; return None if file is absent."""
    if not _CENTROIDS_PATH.exists():
        return None
    try:
        payload: dict[str, list[float]] = json.loads(
            _CENTROIDS_PATH.read_text(encoding="utf-8")
        )
        return {intent: np.array(vec, dtype=np.float32) for intent, vec in payload.items()}
    except Exception:  # noqa: BLE001
        return None


def _init_centroids() -> None:
    """Populate INTENT_CENTROIDS at module init (load or build+save)."""
    global INTENT_CENTROIDS
    loaded = _load_centroids()
    if loaded is not None and set(loaded.keys()) == set(VALID_INTENTS):
        INTENT_CENTROIDS = loaded
        return
    # Build from seed sentences
    model = _ensure_model()
    centroids = _build_centroids(model)
    _save_centroids(centroids)
    INTENT_CENTROIDS = centroids


# Run at import time (populates INTENT_CENTROIDS).
_init_centroids()

# ---------------------------------------------------------------------------
# Classification helper
# ---------------------------------------------------------------------------

_SIMILARITY_THRESHOLD = 0.5
_FALLBACK_INTENT = "Banking"


def _classify(query: str) -> dict[str, Any]:
    """Classify *query* synchronously and return the result dict."""
    model = _ensure_model()
    query_vec: np.ndarray = model.encode([query], convert_to_numpy=True)[0]

    scores: list[tuple[str, float]] = []
    for intent, centroid in INTENT_CENTROIDS.items():
        sim = _cosine_similarity(query_vec, centroid)
        scores.append((intent, sim))

    scores.sort(key=lambda x: x[1], reverse=True)
    max_label, max_score = scores[0]

    qualifying = [(lbl, s) for lbl, s in scores if s >= _SIMILARITY_THRESHOLD]

    if qualifying:
        primary_label, primary_score = qualifying[0]
    else:
        primary_label = _FALLBACK_INTENT
        primary_score = max_score

    services = INTENT_SERVICE_MAP[primary_label]

    all_intents = [
        {"label": lbl, "confidence": round(float(s), 6)}
        for lbl, s in scores
    ]

    return {
        "intent": primary_label,
        "confidence": round(float(primary_score), 6),
        "services": services,
        "all_intents": all_intents,
    }


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

async def _intent_router_impl(state: OrchestratorState) -> dict[str, Any]:
    """Inner async classification coroutine (wrapped with timeout + retry)."""
    query: str = state.get("raw_query", "")

    # Run blocking inference in the default thread-pool executor.
    # asyncio.get_event_loop() is deprecated in 3.10+; use get_running_loop().
    loop = asyncio.get_running_loop()
    result = await asyncio.wait_for(
        loop.run_in_executor(None, _classify, query),
        timeout=2.0,
    )
    return result


_retryable_impl = retryable_node(_intent_router_impl)


async def intent_router_node(state: OrchestratorState) -> dict[str, Any]:
    """LangGraph node: classify intent with automatic fallback guarantee.

    Wraps the retryable inner implementation and ensures the returned dict
    *always* contains a valid ``intent`` and ``confidence``, even if the
    underlying classification fails after all retries (e.g. timeout).
    """
    result = await _retryable_impl(state)

    # If the inner node exhausted retries it returns only execution_trace /
    # errors — patch in the Banking fallback so downstream nodes are safe.
    if result.get("intent") not in VALID_INTENTS:
        result = {
            **result,
            "intent": _FALLBACK_INTENT,
            "confidence": 0.0,
            "services": INTENT_SERVICE_MAP[_FALLBACK_INTENT],
            "all_intents": [
                {"label": lbl, "confidence": 0.0} for lbl in VALID_INTENTS
            ],
        }

    return result


intent_router_node.__name__ = "intent_router"
