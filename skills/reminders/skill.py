"""
JARVIS Reminders & Scheduling Skill
"""

from typing import List, Dict, Any
from skills.base import BaseSkill, SkillManifest
from backend.tasks.scheduler import TaskScheduler


class RemindersSkill(BaseSkill):
    def __init__(self, task_scheduler: TaskScheduler):
        manifest = SkillManifest(
            name="reminders",
            version="1.0.0",
            description="Task scheduling and timed reminders.",
            capabilities=["schedule_reminder", "list_tasks", "cancel_task"],
            required_tools=[],
            permissions_required=[1]
        )
        super().__init__(manifest)
        self.scheduler = task_scheduler

    async def initialize(self) -> bool:
        return True

    def get_tools(self) -> List[Any]:
        return []

    async def execute_capability(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if capability == "schedule_reminder":
            task = self.scheduler.create_task(
                title=params.get("title", "Reminder"),
                description=params.get("description", ""),
                scheduled_delay_seconds=params.get("delay_seconds", 60.0)
            )
            return {"success": True, "task": task.model_dump()}
        elif capability == "list_tasks":
            tasks = self.scheduler.list_tasks(status=params.get("status"))
            return {"success": True, "tasks": [t.model_dump() for t in tasks]}
        elif capability == "cancel_task":
            ok = self.scheduler.update_task_status(params.get("task_id", ""), "CANCELLED")
            return {"success": ok}
        return {"success": False, "error": f"Unknown capability '{capability}'"}
