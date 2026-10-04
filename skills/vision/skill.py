"""
JARVIS Vision Skill
Live screen capture and visual scene understanding.
"""

from typing import List, Dict, Any
from pathlib import Path
from skills.base import BaseSkill, SkillManifest
from backend.tools import ScreenVisionTool


class VisionSkill(BaseSkill):
    def __init__(self, scratch_dir: Path):
        manifest = SkillManifest(
            name="vision",
            version="1.0.0",
            description="Live screen capture and multimodal analysis.",
            capabilities=["capture_screen"],
            required_tools=["screen"],
            permissions_required=[0]
        )
        super().__init__(manifest)
        self.tool = ScreenVisionTool(scratch_dir)

    async def initialize(self) -> bool:
        return True

    def get_tools(self) -> List[Any]:
        return [self.tool]

    async def execute_capability(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if capability == "capture_screen":
            res = await self.tool.execute(params)
            return {"success": res.success, "output": res.output, "error": res.error, "raw_data": res.raw_data}
        return {"success": False, "error": f"Unknown capability '{capability}'"}
