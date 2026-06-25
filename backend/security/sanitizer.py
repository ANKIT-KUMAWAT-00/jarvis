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
