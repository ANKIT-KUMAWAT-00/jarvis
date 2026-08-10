"""
JARVIS Verification Engine
Validates execution receipts against expected postconditions.
Upholds the core law: Never claim an action succeeded unless verified by proof.
"""

from typing import Dict, Any, Optional
from backend.tools.base import Tool, ToolResult, VerificationResult


