"""BGE-M3 embedding model — loaded once at module startup."""
from __future__ import annotations

from typing import Any

_BGE_MODEL: Any = None


def _ensure_bge_model() -> Any:
    global _BGE_MODEL
    if _BGE_MODEL is None:
        from FlagEmbedding import BGEM3FlagModel  # type: ignore
        _BGE_MODEL = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
    return _BGE_MODEL


def _warmup_sync() -> None:
    model = _ensure_bge_model()
    # Run one real inference too — the first .encode() call pays its own
    # lazy-init cost (thread pools, kernel setup) on top of just loading
    # the model weights, so skipping this would still stall the first
    # real chat request.
    model.encode(["warmup"], batch_size=1)


async def warmup() -> None:
    """Load the BGE-M3 model and run one inference at startup so the first
    real request doesn't pay the (multi-GB download + load + first-call)
    cost and risk a client timeout."""
    import asyncio

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _warmup_sync)


async def embed_query(text: str) -> list[float]:
    """Embed a single query string with BGE-M3; returns a 1024-dim vector."""
    import asyncio

    model = _ensure_bge_model()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: model.encode([text], batch_size=1)["dense_vecs"][0].tolist(),
    )
    return result
