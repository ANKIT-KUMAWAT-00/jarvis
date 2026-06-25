"""
JARVIS Prompt Injection Guard & External Content Isolator
Ensures all external web pages, emails, documents, and tool outputs
are strictly isolated as UNTRUSTED DATA and cannot override system instructions.
"""

import re
from typing import Tuple

INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"(?i)disregard\s+(all\s+)?(system|safety|security|policy|\s)+rules",
    r"(?i)you\s+are\s+now\s+(in\s+developer\s+mode|dan|unrestricted)",
    r"(?i)system\s*:\s*new\s+rule",
    r"(?i)reveal\s+(your\s+)?(system\s+prompt|instructions|secret|api[_-]?key)",
    r"(?i)send\s+(the\s+)?(api[_-]?key|credentials|passwords?)\s+to",
    r"(?i)curl\s+.*https?://[a-zA-Z0-9\.\-]+/.*(key|token|secret)",
]


