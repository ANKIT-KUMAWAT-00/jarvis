"""
JARVIS Task State Manager
Maintains task execution state across permission prompts, App Store installations,
multi-turn interruptions, and seamless 'Continue' resumption.
"""

import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.providers.base import PlanResult, PlanStep


class ExecutionState(BaseModel):
    task_id: str
    original_goal: str
    status: str = "PENDING"  # PENDING, IN_PROGRESS, PAUSED_PERMISSION, PAUSED_INSTALLATION, COMPLETED, FAILED, CANCELLED
    plan: Optional[PlanResult] = None
    current_step_index: int = 0
    completed_steps: List[Dict[str, Any]] = Field(default_factory=list)
    pending_steps: List[Dict[str, Any]] = Field(default_factory=list)
    receipts: List[str] = Field(default_factory=list)
    pause_reason: Optional[str] = None
    pause_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class TaskStateManager:
    """Manages active, paused, and historical task execution lifecycles."""

    def __init__(self, max_history: int = 15):
        self.active_task: Optional[ExecutionState] = None
        self.pending_paused_task: Optional[ExecutionState] = None
        self.task_history: List[ExecutionState] = []
        self.max_history = max_history

    @property
    def current_state(self) -> Optional[ExecutionState]:
        return self.active_task

    def start_task(self, goal: str, plan: PlanResult) -> ExecutionState:
        """Initialize an active execution state."""
        task_id = f"T-{int(time.time() * 1000)}"
        steps_dict = [s.model_dump() for s in plan.steps]
        state = ExecutionState(
            task_id=task_id,
            original_goal=goal,
            status="IN_PROGRESS",
            plan=plan,
            current_step_index=0,
            completed_steps=[],
            pending_steps=steps_dict,
            receipts=[]
        )
        self.active_task = state
        return state

    def pause_for_permission(self, pane: str, prompt: str) -> ExecutionState:
        """Pause active task awaiting macOS privacy/security authorization."""
        if not self.active_task:
            raise RuntimeError("No active task to pause.")

        self.active_task.status = "PAUSED_PERMISSION"
        self.active_task.pause_reason = "mac_permission"
        self.active_task.pause_metadata = {
            "type": "MAC_PERMISSION",
            "pane": pane,
            "prompt": prompt,
            "waiting_for": "permission_grant"
        }
        self.active_task.updated_at = time.time()
        self.pending_paused_task = self.active_task
        return self.active_task

    def pause_for_installation(self, app_name: str, store_url: str, prompt: str) -> ExecutionState:
        """Pause active task awaiting Mac App Store installation."""
        if not self.active_task:
            raise RuntimeError("No active task to pause.")

        self.active_task.status = "PAUSED_INSTALLATION"
        self.active_task.pause_reason = "app_install"
        self.active_task.pause_metadata = {
            "type": "APP_INSTALL",
            "app_name": app_name,
            "store_url": store_url,
            "prompt": prompt,
            "waiting_for": "app_store_approval"
        }
        self.active_task.updated_at = time.time()
        self.pending_paused_task = self.active_task
        return self.active_task

    def advance_step(self, receipt: str):
        """Record completed step and progress index."""
        if not self.active_task:
            return

        self.active_task.receipts.append(receipt)
        if self.active_task.pending_steps:
            completed = self.active_task.pending_steps.pop(0)
            self.active_task.completed_steps.append(completed)
        self.active_task.current_step_index += 1
        self.active_task.updated_at = time.time()

    def complete_task(self, summary: str = "") -> ExecutionState:
        """Mark task as successfully completed."""
        state = self.active_task or self.pending_paused_task
        if state:
            state.status = "COMPLETED"
            state.updated_at = time.time()
            self._archive(state)
        self.active_task = None
        self.pending_paused_task = None
        return state

    def fail_task(self, reason: str) -> ExecutionState:
        """Mark task as failed."""
        state = self.active_task or self.pending_paused_task
        if state:
            state.status = "FAILED"
            state.pause_reason = reason
            state.updated_at = time.time()
            self._archive(state)
        self.active_task = None
        self.pending_paused_task = None
        return state

    def cancel_task(self) -> Optional[ExecutionState]:
        """Cancel current active or paused task."""
        state = self.active_task or self.pending_paused_task
        if state:
            state.status = "CANCELLED"
            state.updated_at = time.time()
            self._archive(state)
        self.active_task = None
        self.pending_paused_task = None
        return state

    def get_resumable_task(self) -> Optional[ExecutionState]:
        """Return pending paused task if available."""
        return self.pending_paused_task or self.active_task

    def resume_task(self) -> Optional[ExecutionState]:
        """Unpause pending task to resume execution loop from current step."""
        if self.pending_paused_task:
            state = self.pending_paused_task
            state.status = "IN_PROGRESS"
            state.updated_at = time.time()
            self.active_task = state
            self.pending_paused_task = None
            return state
        return self.active_task

    def _archive(self, state: ExecutionState):
        self.task_history.append(state)
        if len(self.task_history) > self.max_history:
            self.task_history.pop(0)
