"""
Unit tests for JARVIS Permission Engine and Narrow Confirmation Tokens.
"""

import pytest
import time
from backend.security.permissions import PermissionEngine, ActionLevel, ConfirmationToken


def test_permission_levels_auto_authorization():
    engine = PermissionEngine()
    
    # Level 0 (Read) is auto-authorized
    p0, token0, _ = engine.verify_permission("filesystem", "read_file", "README.md", ActionLevel.LEVEL_0_READ)
    assert p0 is True
    assert token0 is None

    # Level 1 (Safe Write) is auto-authorized
    p1, token1, _ = engine.verify_permission("filesystem", "write_file", "notes.txt", ActionLevel.LEVEL_1_SAFE_WRITE)
    assert p1 is True
    assert token1 is None


def test_level_2_external_requires_token():
    engine = PermissionEngine()
    
    # First attempt without token must be blocked and return a narrow token
    permitted, token, reason = engine.verify_permission("git", "push", "origin/main", ActionLevel.LEVEL_2_EXTERNAL)
    assert permitted is False
    assert token is not None
    assert token.tool_name == "git"
    assert token.action_name == "push"
    assert token.target == "origin/main"
    assert "Level 2" in reason


