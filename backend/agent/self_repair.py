"""
JARVIS Self-Repair Engine
Analyzes failures, diagnoses root causes, and formulates minimal corrective actions
within strict retry bounds.
"""

from typing import Dict, Any, Optional
from backend.providers.base import LLMProvider, PlanStep
