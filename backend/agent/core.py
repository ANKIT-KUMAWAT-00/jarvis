"""
JARVIS Autonomous Agent Core
Coordinates Intent Understanding -> Planning -> Safety Check -> Execution ->
Observation -> Verification -> Memory Update -> Truthful Response.
"""

import asyncio
import os
import time
from typing import Dict, Any, Optional, List, Callable
from backend.config import JarvisConfig
from backend.providers.base import LLMProvider, PlanResult, PlanStep
from backend.tools.registry import ToolRegistry
from backend.tools.base import ToolResult, VerificationResult
