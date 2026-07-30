"""
JARVIS Tool Registry & Dispatch Hub
Coordinates tool execution, enforces permission checks via PermissionEngine,
and logs structured receipts into the audit trail.
"""

from typing import Dict, Any, List, Optional
from .base import Tool, ToolResult, VerificationResult
from backend.security.permissions import PermissionEngine, ActionLevel, ConfirmationToken
from backend.memory.store import MemoryStore, ActivityRecord


class ToolRegistry:
    def __init__(self, permission_engine: PermissionEngine, memory_store: MemoryStore):
        self.permission_engine = permission_engine
        self.memory_store = memory_store
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "permission_level": int(t.permission_level),
                "timeout_seconds": t.timeout_seconds
            }
            for t in self._tools.values()
        ]

    async def execute_tool(
        self,
        name: str,
        params: Dict[str, Any],
        token_id: Optional[str] = None,
        task_id: str = "T-DIRECT"
    ) -> tuple[ToolResult, Optional[ConfirmationToken]]:
        """
        Dispatches tool execution with strict permission verification.
        Returns (ToolResult, ConfirmationToken).
        """
        tool = self._tools.get(name)
        if not tool:
            res = ToolResult(success=False, output="", error=f"Tool '{name}' is not registered.")
            return res, None

        # Determine target of action
        action_name = params.get("action", "execute")
        target = str(params.get("path") or params.get("command") or params.get("url") or params.get("name") or "default")

        # Determine dynamic risk level
        effective_risk = tool.permission_level
        if name == "filesystem" and action_name == "delete_file":
            effective_risk = ActionLevel.LEVEL_3_HIGH_RISK
        elif name == "terminal" and params.get("command"):
            from backend.security.sanitizer import Sanitizer
            is_dest, _ = Sanitizer.is_destructive_command(params["command"])
            if is_dest:
                effective_risk = ActionLevel.LEVEL_3_HIGH_RISK
        elif name == "git" and action_name == "push":
            effective_risk = ActionLevel.LEVEL_2_EXTERNAL

        # Check permissions
        is_permitted, token, reason = self.permission_engine.verify_permission(
            tool_name=name,
            action_name=action_name,
            target=target,
            risk_level=effective_risk,
            token_id=token_id
        )

        if not is_permitted:
            res = ToolResult(
                success=False,
                output="",
                error=f"Permission Denied: {reason}",
                raw_data={"token_id": token.token_id if token else None, "risk_level": int(effective_risk)}
            )
            # Log pending permission intercept
            self.memory_store.log_activity(ActivityRecord(
                task_id=task_id,
                tool_name=name,
                action=action_name,
                status="WAITING_FOR_PERMISSION",
                duration_ms=0,
                error_category="PERMISSION_REQUIRED"
            ))
            return res, token

        # If authorized for high risk, pass flag
        if effective_risk == ActionLevel.LEVEL_3_HIGH_RISK:
            params["authorized_high_risk"] = True

        # Execute
        result = await tool.execute(params)

        # Log audit trail
        self.memory_store.log_activity(ActivityRecord(
            task_id=task_id,
            tool_name=name,
            action=action_name,
            status="SUCCESS" if result.success else "FAILED",
            duration_ms=result.execution_time_ms,
            error_category=None if result.success else "EXECUTION_ERROR"
        ))

        return result, None
