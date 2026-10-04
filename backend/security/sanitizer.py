"""
JARVIS Sanitizer & Path Boundary Protector
Enforces filesystem containment, secret masking, and dangerous command interception.
"""

import os
import re
from pathlib import Path
from typing import Tuple, List

# Patterns of sensitive files and directories that must NEVER be accessed without Level 3 confirmation
PROTECTED_PATHS = [
    ".ssh",
    ".aws",
    ".gnupg",
    ".bash_history",
    ".zsh_history",
    "/etc/shadow",
    "/etc/passwd",
    "/etc/sudoers",
    "id_rsa",
    "id_ed25519",
]

# Patterns for destructive or dangerous commands
DESTRUCTIVE_COMMAND_PATTERNS = [
    r"\brm\s+(-[rfRF]{1,4}\s+|--recursive\s+|--force\s+)*[/~]",  # rm -rf / or rm -rf ~
    r"\brm\s+-[rfRF]{1,4}\s+\*",                                 # rm -rf *
    r"\bmkfs\b",                                                 # format disk
    r"\bfdisk\b",
    r"\bdd\s+if=",                                               # raw disk write
    r"\bchmod\s+(-R\s+)?(777|000)\b",                           # unsafe permissions
    r"\bchown\s+-R\b",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",                     # fork bomb
    r"\bshutdown\b",
    r"\breboot\b",
    r">\s*/dev/sd[a-z]",                                         # direct device overwriting
]

# Secret regex patterns to redact
SECRET_PATTERNS = [
    (r"(?i)(api[_\s-]?key|secret|password|passwd|token|bearer|auth[_\s-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", r"\1: [REDACTED]"),
    (r"AIza[0-9A-Za-z\-_]{25,45}", "[GEMINI_API_KEY_REDACTED]"),
    (r"sk-[a-zA-Z0-9]{20,60}", "[API_KEY_REDACTED]"),
    (r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----", "[PRIVATE_KEY_REDACTED]"),
]


class Sanitizer:
    @staticmethod
    def mask_secrets(text: str) -> str:
        """Sanitizes text by masking API keys, credentials, and private keys."""
        if not text:
            return ""
        sanitized = text
        for pattern, replacement in SECRET_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized)
        return sanitized

    @staticmethod
    def validate_path(target_path: Path | str, workspace_root: Path) -> Tuple[bool, Path, str]:
        """
        Validates whether target_path resides safely within workspace_root.
        Prevents directory traversal and access to sensitive locations.
        """
        try:
            raw_path = Path(target_path).expanduser()
            if not raw_path.is_absolute():
                resolved = (workspace_root / raw_path).resolve()
            else:
                resolved = raw_path.resolve()

            resolved_str = str(resolved)

            # Check protected system paths
            for protected in PROTECTED_PATHS:
                if protected in resolved_str:
                    return False, resolved, f"Access to sensitive path pattern '{protected}' is strictly blocked."

            # Check workspace boundary containment
            try:
                resolved.relative_to(workspace_root.resolve())
            except ValueError:
                # Outside workspace
                return False, resolved, f"Path '{resolved_str}' lies outside authorized workspace '{workspace_root}'."

            return True, resolved, "Path is valid and contained within workspace."
        except Exception as e:
            return False, Path("/dev/null"), f"Path resolution failed: {str(e)}"

    @staticmethod
    def is_destructive_command(command: str) -> Tuple[bool, str]:
        """Checks if a shell command contains destructive or high-risk patterns."""
        cmd_clean = command.strip()
        for pattern in DESTRUCTIVE_COMMAND_PATTERNS:
            if re.search(pattern, cmd_clean):
                return True, f"Command matches high-risk destructive signature: '{pattern}'"
        
        # Check for direct rm -rf commands
        if re.search(r"\brm\s+-[rfRF]{1,4}\b", cmd_clean):
            return True, "Command includes recursive force removal."

        # Check for git destructive actions
        if re.search(r"\bgit\s+reset\s+--hard\b", cmd_clean):
            return True, "Command includes hard git reset which discards uncommitted work."
        if re.search(r"\bgit\s+push\s+.*--force\b", cmd_clean):
            return True, "Command includes force pushing to remote repository."

        return False, "Command appears standard."
