"""End-to-end chat pipeline integration tests.

All external dependencies (vLLM, Qdrant, DB) are mocked.
Tests the full FastAPI app via httpx.AsyncClient.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_jwt_user():
    """Return a mock authenticated user."""
    user = MagicMock()
    user.id = 1
    user.first_name = "Test"
    user.is_active = True
    user.is_blocked = False
    return user


@pytest.mark.asyncio
async def test_single_intent_chat_returns_200(mock_jwt_user):
    """POST /ai/chat with a portfolio question returns HTTP 200 with all schema fields."""
    from ai.api.deps import get_ai_current_user
    from ai.agents.response_formatter import REQUIRED_KEYS

    mock_result = {
        "session_id": "test-session",
        "message": "Your portfolio looks balanced.",
        "charts": [],
        "recommendations": [],
        "portfolio": [],
        "confidence": 0.8,
        "citations": [],
        "metadata": {
            "intent": "Portfolio_Review",
            "services_invoked": ["portfolio"],
            "latency_ms": 100,
            "session_degraded": False,
            "errors": [],
        },
    }

    with patch("ai.api.chat.graph") as mock_chat_graph:
        mock_chat_graph.ainvoke = AsyncMock(return_value={"formatted_response": mock_result})

        from ai.main import app
        app.dependency_overrides[get_ai_current_user] = lambda: mock_jwt_user

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/ai/chat",
                    json={"message": "What should I do with my portfolio?"},
                    headers={"Authorization": "Bearer fake-token"},
                )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    for key in REQUIRED_KEYS:
        assert key in data, f"Required key '{key}' missing from response"
    assert data["metadata"]["intent"] == "Portfolio_Review"


@pytest.mark.asyncio
async def test_pipeline_timeout_returns_504(mock_jwt_user):
    """When the pipeline times out, HTTP 504 with PIPELINE_TIMEOUT is returned."""
    from ai.api.deps import get_ai_current_user

    async def _slow_invoke(*args, **kwargs):
        await asyncio.sleep(35)  # exceeds 30s timeout
        return {}

    with patch("ai.api.chat.graph") as mock_chat_graph:
        mock_chat_graph.ainvoke = _slow_invoke

        from ai.main import app
        app.dependency_overrides[get_ai_current_user] = lambda: mock_jwt_user

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/ai/chat",
                    json={"message": "Show me my portfolio."},
                    headers={"Authorization": "Bearer fake-token"},
                    timeout=40.0,
                )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 504
    data = response.json()
    assert data["detail"]["error_code"] == "PIPELINE_TIMEOUT"


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401():
    """Request without Authorization header returns HTTP 401."""
    from ai.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/ai/chat", json={"message": "Hello"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_message_too_long_returns_422(mock_jwt_user):
    """Message exceeding 2000 characters returns HTTP 422."""
    from ai.api.deps import get_ai_current_user
    from ai.main import app
    app.dependency_overrides[get_ai_current_user] = lambda: mock_jwt_user
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/ai/chat",
                json={"message": "x" * 2001},
                headers={"Authorization": "Bearer fake-token"},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    """GET /ai/health returns HTTP 200 with status and dependency fields."""
    with patch("ai.api.health.get_redis") as mock_redis_factory, \
         patch("ai.api.health.ai_async_engine") as mock_engine, \
         patch("httpx.AsyncClient") as mock_http:
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis_factory.return_value = mock_redis

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_conn

        mock_http_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_http_instance.get = AsyncMock(return_value=mock_response)
        mock_http_instance.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http_instance.__aexit__ = AsyncMock(return_value=False)
        mock_http.return_value = mock_http_instance

        from ai.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ai/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
