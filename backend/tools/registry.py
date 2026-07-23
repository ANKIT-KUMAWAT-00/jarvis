"""
JARVIS Tool Registry & Dispatch Hub
Coordinates tool execution, enforces permission checks via PermissionEngine,
and logs structured receipts into the audit trail.
"""

from typing import Dict, Any, List, Optional
from .base import Tool, ToolResult, VerificationResult
