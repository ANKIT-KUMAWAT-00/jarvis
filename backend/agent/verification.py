"""
JARVIS Verification Engine
Validates execution receipts against expected postconditions.
Upholds the core law: Never claim an action succeeded unless verified by proof.
"""

from typing import Dict, Any, Optional
from backend.tools.base import Tool, ToolResult, VerificationResult


class VerificationEngine:
    @staticmethod
    def verify_step(
        tool: Tool,
        result: ToolResult,
        expected_outcome: str,
        parameters: Dict[str, Any]
    ) -> VerificationResult:
        """
        Runs tool-specific verification followed by general consistency checks.
        """
        expectation = {
            "expected": expected_outcome,
            "path": parameters.get("path"),
            "action": parameters.get("action"),
            "name": parameters.get("name"),
            "expected_exit_code": parameters.get("expected_exit_code", 0)
        }

        # First run tool verification
        v_res = tool.verify(result, expectation)
        if not v_res.verified:
            return v_res

        # Enforce consistency check
        if not result.success:
            return VerificationResult(
                verified=False,
                expected=expected_outcome,
                actual=f"Tool error: {result.error}",
                message="Execution reported an error; cannot verify success."
            )

        return VerificationResult(
            verified=True,
            expected=expected_outcome,
            actual=v_res.actual,
            message="Verified successfully with concrete receipt."
        )

    @staticmethod
    def format_receipt(verification: VerificationResult) -> str:
        status_symbol = "✓ VERIFIED" if verification.verified else "✗ UNVERIFIED"
        return f"[{status_symbol}] Expected: {verification.expected} | Result: {verification.actual}"
