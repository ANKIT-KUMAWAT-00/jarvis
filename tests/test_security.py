"""
Unit and boundary security tests for JARVIS.
"""

import pytest
from pathlib import Path
from backend.security.sanitizer import Sanitizer
from backend.security.guardrails import PromptInjectionGuard


def test_secret_masking():
    raw_text = "API Key: AIzaSyD9834873294823948293849238492384 and token: sk-abcdefghijklmnopqrstuvwxyz123456"
    masked = Sanitizer.mask_secrets(raw_text)
    assert "AIza" not in masked
    assert "sk-" not in masked
    assert "[REDACTED]" in masked


