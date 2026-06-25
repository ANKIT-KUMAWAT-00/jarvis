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


def test_path_boundary_containment():
    workspace = Path("/tmp/jarvis_test_workspace").resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    # Valid file inside workspace
    valid, p, _ = Sanitizer.validate_path("sub/file.txt", workspace)
    assert valid is True
    assert p == workspace / "sub" / "file.txt"

    # Directory traversal attack
    valid, _, reason = Sanitizer.validate_path("../../../etc/shadow", workspace)
    assert valid is False
    assert "outside" in reason or "sensitive" in reason

    # Sensitive path pattern attack
    valid, _, reason = Sanitizer.validate_path(".ssh/id_rsa", workspace)
    assert valid is False
    assert "sensitive" in reason.lower()


def test_destructive_command_detection():
    # Destructive commands
    assert Sanitizer.is_destructive_command("rm -rf /")[0] is True
    assert Sanitizer.is_destructive_command("rm -rf ~")[0] is True
    assert Sanitizer.is_destructive_command("mkfs.ext4 /dev/sda1")[0] is True
    assert Sanitizer.is_destructive_command("git reset --hard HEAD~1")[0] is True
    assert Sanitizer.is_destructive_command("git push origin main --force")[0] is True

    # Benign commands
    assert Sanitizer.is_destructive_command("ls -la")[0] is False
    assert Sanitizer.is_destructive_command("npm test")[0] is False
    assert Sanitizer.is_destructive_command("python3 -m pytest")[0] is False


