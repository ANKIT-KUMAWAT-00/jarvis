"""
JARVIS Browser Skill
Safe web content retrieval and semantic parsing.
"""

from typing import List, Dict, Any
from skills.base import BaseSkill, SkillManifest
from backend.tools import BrowserTool


class BrowserSkill(BaseSkill):
    def __init__(self):
        manifest = SkillManifest(
            name="browser",
            version="1.0.0",
            description="Safe web retrieval with untrusted data isolation.",
            capabilities=["fetch_webpage"],
            required_tools=["browser"],
            permissions_required=[0]
        )
        super().__init__(manifest)
        self.tool = BrowserTool()

    async def initialize(self) -> bool:
        return True

    def get_tools(self) -> List[Any]:
        return [self.tool]

    async def execute_capability(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if capability == "fetch_webpage":
            res = await self.tool.execute({"url": params.get("url", "")})
            return {"success": res.success, "output": res.output, "error": res.error}
        return {"success": False, "error": f"Unknown capability '{capability}'"}
