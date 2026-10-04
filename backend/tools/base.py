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


class VerificationResult(BaseModel):
    verified: bool
    expected: str
    actual: str
    message: str


class Tool(ABC):
    """Abstract base class for all JARVIS tools."""
    name: str
    description: str
    permission_level: ActionLevel = ActionLevel.LEVEL_0_READ
    timeout_seconds: float = 30.0

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute the tool with provided arguments."""
        pass

    def verify(self, result: ToolResult, expectation: Dict[str, Any]) -> VerificationResult:
        """
        Verify whether the tool execution achieved its expected condition.
        Default verification validates that execution succeeded without errors.
        """
        if not result.success:
            return VerificationResult(
                verified=False,
                expected=str(expectation.get("expected", "Success status True")),
                actual=f"Failed with error: {result.error}",
                message="Tool reported execution failure."
            )
        return VerificationResult(
            verified=True,
            expected=str(expectation.get("expected", "Success status True")),
            actual="Execution succeeded cleanly.",
            message="Default verification passed."
        )
