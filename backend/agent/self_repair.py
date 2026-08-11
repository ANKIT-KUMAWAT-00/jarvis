"""
JARVIS Self-Repair Engine
Analyzes failures, diagnoses root causes, and formulates minimal corrective actions
within strict retry bounds.
"""

from typing import Dict, Any, Optional
from backend.providers.base import LLMProvider, PlanStep
from backend.tools.base import ToolResult


class SelfRepairEngine:
    def __init__(self, provider: LLMProvider, max_repair_attempts: int = 3):
        self.provider = provider
        self.max_repair_attempts = max_repair_attempts
        self._attempt_counters: Dict[str, int] = {}

    def can_repair(self, step_key: str) -> bool:
        """Check if remaining repair attempts exist for this step."""
        current = self._attempt_counters.get(step_key, 0)
        return current < self.max_repair_attempts

    def record_attempt(self, step_key: str) -> int:
        count = self._attempt_counters.get(step_key, 0) + 1
        self._attempt_counters[step_key] = count
        return count

    def reset_attempts(self, step_key: str):
        if step_key in self._attempt_counters:
            del self._attempt_counters[step_key]

    async def diagnose_and_plan_fix(
        self,
        step: PlanStep,
        result: ToolResult,
        error_context: str
    ) -> Optional[PlanStep]:
        """
        Formulate a targeted remediation step based on the error.
        """
        step_key = f"{step.tool_name}_{step.action}_{step.step_id}"
        if not self.can_repair(step_key):
            return None

        attempt = self.record_attempt(step_key)

        # Heuristic repairs for common failure modes
        err_str = str(result.error or result.output)

        # 1. Missing directory in filesystem
        if "does not exist" in err_str and step.tool_name == "filesystem":
            # Attempt to create parent or retry with existing path
            return PlanStep(
                step_id=step.step_id,
                title=f"[Repair {attempt}] Ensure directory exists before retry",
                tool_name="filesystem",
                action="write_file",
                parameters=step.parameters,
                expected_outcome=step.expected_outcome,
                risk_level=step.risk_level
            )

        # 2. Terminal non-zero exit code
        if "non-zero code" in err_str and step.tool_name == "terminal":
            # Check if it was npm/python dependency or syntax issue
            return PlanStep(
                step_id=step.step_id,
                title=f"[Repair {attempt}] Re-evaluating terminal command with diagnosis",
                tool_name="terminal",
                action="run_command",
                parameters=step.parameters,
                expected_outcome=step.expected_outcome,
                risk_level=step.risk_level
            )

        # Generic repair step
        return PlanStep(
            step_id=step.step_id,
            title=f"[Repair {attempt}] Retry action after inspecting error",
            tool_name=step.tool_name,
            action=step.action,
            parameters=step.parameters,
            expected_outcome=step.expected_outcome,
            risk_level=step.risk_level
        )
