"""
JARVIS Security & Permission Engine
Implements strict Action Levels (LEVEL 0 to LEVEL 3) and narrow confirmation tokens.
"""

from enum import IntEnum
import time
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ActionLevel(IntEnum):
    LEVEL_0_READ = 0        # Read-only operations, zero confirmation needed
    LEVEL_1_SAFE_WRITE = 1  # Safe workspace writes, auto-performed on user intent
    LEVEL_2_EXTERNAL = 2    # External actions (push, external calls), confirmation required
    LEVEL_3_HIGH_RISK = 3   # Destructive commands, data deletion, force push: ALWAYS confirmed


class ConfirmationToken(BaseModel):
    token_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    action_name: str
    target: str
    risk_level: ActionLevel
    explanation: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    expires_at: float = Field(default_factory=lambda: time.time() + 300) # 5 min expiry
    is_confirmed: bool = False
    is_rejected: bool = False


class PermissionEngine:
    def __init__(self):
        self._pending_tokens: Dict[str, ConfirmationToken] = {}
        self._standing_permissions: Dict[str, bool] = {}

    def create_token(
        self,
        tool_name: str,
        action_name: str,
        target: str,
        risk_level: ActionLevel,
        explanation: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> ConfirmationToken:
        """Create a narrow, single-action confirmation token."""
        token = ConfirmationToken(
            tool_name=tool_name,
            action_name=action_name,
            target=target,
            risk_level=risk_level,
            explanation=explanation,
            parameters=parameters or {}
        )
        self._pending_tokens[token.token_id] = token
        return token

    def verify_permission(
        self,
        tool_name: str,
        action_name: str,
        target: str,
        risk_level: ActionLevel,
        token_id: Optional[str] = None
    ) -> tuple[bool, Optional[ConfirmationToken], str]:
        """
        Evaluate if an action is permitted.
        Returns (is_permitted, confirmation_token, reason).
        """
        # Level 0 & Level 1 are authorized automatically if requested by user
        if risk_level in (ActionLevel.LEVEL_0_READ, ActionLevel.LEVEL_1_SAFE_WRITE):
            return True, None, "Authorized by user request policy."

        # Level 2 & Level 3 require active token verification
        if not token_id:
            token = self.create_token(
                tool_name=tool_name,
                action_name=action_name,
                target=target,
                risk_level=risk_level,
                explanation=f"Action '{action_name}' on '{target}' requires explicit Level {risk_level} confirmation."
            )
            return False, token, f"Action requires explicit user confirmation (Level {risk_level})."

        token = self._pending_tokens.get(token_id)
        if not token:
            return False, None, "Invalid or non-existent confirmation token."

        if time.time() > token.expires_at:
            del self._pending_tokens[token_id]
            return False, None, "Confirmation token has expired."

        if token.is_rejected:
            del self._pending_tokens[token_id]
            return False, None, "Action was rejected by user."

        if not token.is_confirmed:
            return False, token, "Action is still pending user confirmation."

        # Narrow check: token must match EXACT tool, action, and target
        if token.tool_name != tool_name or token.action_name != action_name or token.target != target:
            return False, None, "Security violation: token does not match requested action target."

        # Token is one-time use; consume it immediately
        del self._pending_tokens[token_id]
        return True, token, "Action authorized by verified narrow confirmation token."

    def confirm_token(self, token_id: str) -> bool:
        """Mark a pending token as confirmed."""
        token = self._pending_tokens.get(token_id)
        if token and time.time() <= token.expires_at:
            token.is_confirmed = True
            return True
        return False

    def reject_token(self, token_id: str) -> bool:
        """Mark a pending token as rejected."""
        token = self._pending_tokens.get(token_id)
        if token:
            token.is_rejected = True
            return True
        return False

    def get_pending_token(self, token_id: str) -> Optional[ConfirmationToken]:
        token = self._pending_tokens.get(token_id)
        if token and time.time() <= token.expires_at:
            return token
        return None
