"""
JARVIS Mock LLM Provider
Deterministic, zero-cost high-fidelity provider for offline execution,
unit tests, preflight checks, and demonstrations without API keys.
"""

import json
import re
import urllib.parse
from typing import List, Dict, Any, Optional, Type
