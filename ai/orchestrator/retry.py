from __future__ import annotations
import asyncio
import time
from ai.orchestrator.state import OrchestratorState


def retryable_node(fn, max_retries: int = 2):
    async def wrapper(state: OrchestratorState) -> dict:
        node_name = fn.__name__
        last_error = None
        for attempt in range(max_retries + 1):
            start_ms = int(time.time() * 1000)
            try:
                result = await fn(state)
                end_ms = int(time.time() * 1000)
                trace = {
                    "node": node_name,
                    "attempt": attempt,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "error": None,
                }
                existing = list(state.get("execution_trace", []))
                return {**result, "execution_trace": existing + [trace]}
            except Exception as exc:
                last_error = exc
                end_ms = int(time.time() * 1000)
                if attempt == max_retries:
                    trace = {
                        "node": node_name,
                        "attempt": attempt,
                        "start_ms": start_ms,
                        "end_ms": end_ms,
                        "error": str(exc),
                    }
                    existing = list(state.get("execution_trace", []))
                    existing_errs = list(state.get("errors", []))
                    return {
                        "execution_trace": existing + [trace],
                        "errors": existing_errs + [f"{node_name}: {exc}"],
                    }
                await asyncio.sleep(0.1 * (attempt + 1))

    wrapper.__name__ = fn.__name__
    return wrapper
