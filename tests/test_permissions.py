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


def test_level_3_high_risk_token_flow():
    engine = PermissionEngine()
    
    # Request destructive operation
    permitted, token, _ = engine.verify_permission(
        "terminal", "rm -rf", "./build", ActionLevel.LEVEL_3_HIGH_RISK
    )
    assert permitted is False
    assert token is not None

    # User confirms token
    ok = engine.confirm_token(token.token_id)
    assert ok is True

    # Re-verify with confirmed token
    permitted_now, consumed_token, reason = engine.verify_permission(
        "terminal", "rm -rf", "./build", ActionLevel.LEVEL_3_HIGH_RISK, token_id=token.token_id
    )
    assert permitted_now is True
    assert consumed_token is not None

    # Verify one-time consumption: using the token a second time must fail!
    p_again, _, err = engine.verify_permission(
        "terminal", "rm -rf", "./build", ActionLevel.LEVEL_3_HIGH_RISK, token_id=token.token_id
    )
    assert p_again is False


def test_token_narrow_scope_tampering_protection():
    engine = PermissionEngine()
    
    # Token created for deleting ./temp
    _, token, _ = engine.verify_permission("terminal", "rm -rf", "./temp", ActionLevel.LEVEL_3_HIGH_RISK)
    engine.confirm_token(token.token_id)

    # Malicious attempt: use token confirmed for ./temp to delete /root instead
    permitted, _, err = engine.verify_permission(
        "terminal", "rm -rf", "/root", ActionLevel.LEVEL_3_HIGH_RISK, token_id=token.token_id
    )
    assert permitted is False
    assert "Security violation" in err


def test_token_rejection():
    engine = PermissionEngine()
    _, token, _ = engine.verify_permission("git", "push", "origin", ActionLevel.LEVEL_2_EXTERNAL)
    
    # Reject token
    engine.reject_token(token.token_id)
    permitted, _, err = engine.verify_permission("git", "push", "origin", ActionLevel.LEVEL_2_EXTERNAL, token_id=token.token_id)
    assert permitted is False
    assert "rejected" in err.lower()
