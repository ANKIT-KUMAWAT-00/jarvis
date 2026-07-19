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
async def test_mock_provider_structured_planning():
    provider = MockProvider()
    plan = await provider.plan("Create a React application called Nova")
    
    assert isinstance(plan, PlanResult)
    assert plan.goal == "Create a React application called Nova"
    assert plan.requires_tools is True
    assert len(plan.steps) >= 3
    assert plan.steps[0].tool_name == "filesystem"
    assert plan.steps[0].action == "list_dir"


@pytest.mark.asyncio
async def test_mock_provider_structured_output():
    provider = MockProvider()
    result = await provider.generate_structured(
        prompt="Analyze safety of operation",
        schema_class=SampleOutputSchema
    )
    assert isinstance(result, SampleOutputSchema)
    assert isinstance(result.intent, str)
    assert isinstance(result.confidence, float)
    assert isinstance(result.is_safe, bool)


@pytest.mark.asyncio
async def test_mock_provider_analysis():
    provider = MockProvider()
    analysis = await provider.analyze(
        content="System metrics: CPU 12%, Memory 4GB free",
        instruction="Summarize CPU utilization"
    )
    assert len(analysis) > 0


def test_gemini_provider_unconfigured_detection():
    # Test when API key is empty or placeholder
    provider = GeminiProvider(api_key="", model_name="gemini-2.5-flash")
    assert not provider.is_configured()
    assert provider.get_model_name() == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_gemini_provider_unconfigured_raises_cleanly():
    provider = GeminiProvider(api_key="", model_name="gemini-2.5-flash")
    with pytest.raises(RuntimeError) as exc_info:
        await provider.chat([{"role": "user", "content": "ping"}])
    assert "not configured" in str(exc_info.value).lower()
