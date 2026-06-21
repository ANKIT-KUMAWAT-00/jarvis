"""
JARVIS Sanitizer & Path Boundary Protector
Enforces filesystem containment, secret masking, and dangerous command interception.
"""

import os
import re
from pathlib import Path
