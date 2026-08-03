"""Integration test — verify AIExecutionTrace row is persisted after a request."""
import hashlib
from unittest.mock import AsyncMock, MagicMock
import pytest
from ai.utils.logging import persist_execution_trace, hash_user_id
from ai.models.ai_tables import AIExecutionTrace


@pytest.mark.asyncio
async def test_execution_trace_persisted():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    await persist_execution_trace(
        request_id="req-123",
        user_id=42,
        session_id="sess-abc",
        endpoint="/ai/chat",
        intent="Portfolio_Review",
        services_invoked=["portfolio", "financial_advisor"],
        node_traces=[{"node": "intent_router", "start_ms": 0, "end_ms": 50, "error": None}],
        total_latency_ms=4200,
        llm_tokens_used=892,
        http_status=200,
        db=db,
    )

    db.add.assert_called_once()
    trace = db.add.call_args[0][0]
    assert isinstance(trace, AIExecutionTrace)
    assert trace.request_id == "req-123"
    assert trace.user_id_hash == hash_user_id(42)
    assert trace.session_id == "sess-abc"
    assert trace.intent == "Portfolio_Review"
    assert trace.http_status == 200
    # Raw user_id must not be stored
    assert trace.user_id_hash != "42"


@pytest.mark.asyncio
async def test_query_hash_in_trace():
    """Verify hash_user_id produces SHA-256 hex digest."""
    expected = hashlib.sha256("42".encode()).hexdigest()
    assert hash_user_id(42) == expected
    assert len(hash_user_id(42)) == 64  # 256-bit hex
