"""
Unit tests for JARVIS LLM Providers (MockProvider, GeminiProvider config, schemas).
"""

import pytest
from pydantic import BaseModel
from backend.providers.base import LLMProvider, PlanResult, PlanStep
from backend.providers.mock import MockProvider
from backend.providers.gemini import GeminiProvider


