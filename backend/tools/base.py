"""
JARVIS Tool Abstraction Base
Defines the Tool interface, ToolResult, VerificationResult, and parameter schemas.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field
from backend.security.permissions import ActionLevel


class ToolResult(BaseModel):
    success: bool
    output: Any
    error: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    execution_time_ms: int = 0


