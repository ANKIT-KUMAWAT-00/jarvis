"""
JARVIS Prompt Injection Guard & External Content Isolator
Ensures all external web pages, emails, documents, and tool outputs
are strictly isolated as UNTRUSTED DATA and cannot override system instructions.
"""

import re
from typing import Tuple

