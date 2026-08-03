"""Tests for ai/agents/financial_advisor.py — Tasks 15.1–15.8.

Three mocked tests:
1. Mocked vLLM returns expected LLMOutput shape.
2. LLM_UNAVAILABLE raised on ConnectError.
3. Language instruction included in system prompt for non-English preferred_language.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from ai.agents.financial_advisor import (
    LLMOutput,
    build_system_prompt,
    generate_response,
)


# ---------------------------------------------------------------------------
# Test 1 — Mocked vLLM returns expected LLMOutput shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_response_returns_llm_output_shape():
    """Mocked vLLM call must return an LLMOutput with text, tokens_used, confidence."""
    # Build a mock response that mimics the OpenAI ChatCompletion structure
    mock_choice = MagicMock()
    mock_choice.message.content = "Your portfolio looks balanced."
    mock_choice.logprobs = None  # no logprobs → confidence defaults to 0.7

    mock_usage = MagicMock()
    mock_usage.total_tokens = 42

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    mock_create = AsyncMock(return_value=mock_response)

    with patch("ai.agents.financial_advisor.get_vllm_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_client_factory.return_value = mock_client

        result = await generate_response(
            system_prompt="You are a financial advisor.",
            user_prompt="Review my portfolio.",
        )

    # Verify shape
    assert isinstance(result, LLMOutput), "Result must be an LLMOutput instance"
    assert isinstance(result.text, str), "text must be a str"
    assert isinstance(result.tokens_used, int), "tokens_used must be an int"
    assert isinstance(result.confidence, float), "confidence must be a float"

    # Verify values
    assert result.text == "Your portfolio looks balanced."
    assert result.tokens_used == 42
    assert result.confidence == 0.7  # no logprobs → default


# ---------------------------------------------------------------------------
# Test 2 — LLM_UNAVAILABLE raised on ConnectError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_response_raises_503_on_connect_error():
    """httpx.ConnectError from vLLM must raise HTTPException 503 with LLM_UNAVAILABLE."""
    connect_error = httpx.ConnectError("Connection refused")

    mock_create = AsyncMock(side_effect=connect_error)

    with patch("ai.agents.financial_advisor.get_vllm_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_client_factory.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await generate_response(
                system_prompt="You are a financial advisor.",
                user_prompt="What should I invest in?",
            )

    exc = exc_info.value
    assert exc.status_code == 503, f"Expected 503, got {exc.status_code}"
    assert exc.detail["error_code"] == "LLM_UNAVAILABLE", (
        f"Expected error_code 'LLM_UNAVAILABLE', got {exc.detail}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Language instruction included for non-English preferred_language
# ---------------------------------------------------------------------------


def test_build_system_prompt_includes_language_instruction_for_hindi():
    """When preferred_language='hi', system prompt must include the IMPORTANT lang instruction."""
    user_context = {
        "user": {
            "first_name": "Ravi",
            "city": "Mumbai",
            "state": "Maharashtra",
            "preferred_language": "hi",
        },
        "financial_profile": {
            "risk_profile": "moderate",
            "investment_horizon_years": 10,
        },
    }
    prompt = build_system_prompt(user_context)

    assert "IMPORTANT" in prompt, "Language instruction must contain 'IMPORTANT'"
    assert "hi" in prompt, "Language code 'hi' must appear in the prompt"
    assert "Respond in hi" in prompt, "Prompt must instruct the model to respond in Hindi"


def test_build_system_prompt_no_language_instruction_for_english():
    """When preferred_language='en', NO language instruction should be added."""
    user_context = {
        "user": {
            "first_name": "Alice",
            "city": "Delhi",
            "state": "Delhi",
            "preferred_language": "en",
        },
        "financial_profile": {
            "risk_profile": "aggressive",
            "investment_horizon_years": 7,
        },
    }
    prompt = build_system_prompt(user_context)

    assert "IMPORTANT" not in prompt, (
        "No IMPORTANT language instruction expected for English preferred_language"
    )
