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
