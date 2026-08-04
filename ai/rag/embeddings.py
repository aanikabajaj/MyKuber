"""RAG embedding model — loaded once at module startup.

Uses all-MiniLM-L6-v2 (384-dim, ~90MB) rather than BGE-M3 (~2GB) so the
whole AI gateway fits in a memory-constrained free-tier host. Retrieval
quality is somewhat lower than BGE-M3 would give, but this is the same
model already bundled for intent_router's semantic classifier, so no
extra download.
"""
from __future__ import annotations

from typing import Any

_MODEL: Any = None


def _ensure_model() -> Any:
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def _warmup_sync() -> None:
    model = _ensure_model()
    # Run one real inference too — the first .encode() call pays its own
    # lazy-init cost (thread pools, kernel setup) on top of just loading
    # the model weights, so skipping this would still stall the first
    # real chat request.
    model.encode(["warmup"], convert_to_numpy=True)


async def warmup() -> None:
    """Load the embedding model and run one inference at startup so the
    first real request doesn't pay the (download + load + first-call)
    cost and risk a client timeout."""
    import asyncio

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _warmup_sync)


async def embed_query(text: str) -> list[float]:
    """Embed a single query string; returns a 384-dim vector."""
    import asyncio

    model = _ensure_model()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: model.encode([text], convert_to_numpy=True)[0].tolist(),
    )
    return result
