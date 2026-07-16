"""
Unit tests for JARVIS LLM Providers (MockProvider, GeminiProvider config, schemas).
"""

import pytest
from pydantic import BaseModel
from backend.providers.base import LLMProvider, PlanResult, PlanStep
from backend.providers.mock import MockProvider
from backend.providers.gemini import GeminiProvider


class SampleOutputSchema(BaseModel):
    intent: str
    confidence: float
    is_safe: bool


@pytest.mark.asyncio
async def test_mock_provider_chat_responses():
    provider = MockProvider()
    assert provider.is_configured()
    assert "mock" in provider.get_model_name().lower()

    # Test personality greeting
    greeting = await provider.chat([{"role": "user", "content": "Hello JARVIS"}])
    assert "Sir" in greeting
    assert "operational" in greeting

    # Test status check
    status = await provider.chat([{"role": "user", "content": "JARVIS, what is the system status?"}])
    assert "Sir" in status
    assert "green" in status or "operational" in status


@pytest.mark.asyncio
