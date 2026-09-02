"""
Comprehensive Security Audit Tests for JARVIS.
Verifies all security boundaries, injection defenses, and containment rules.
"""

import pytest
from pathlib import Path
from backend.security.sanitizer import Sanitizer
from backend.security.guardrails import PromptInjectionGuard
