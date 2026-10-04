"""
JARVIS Filesystem Skill
Sandboxed file and directory operations with strict path containment.
"""

from typing import List, Dict, Any
from pathlib import Path
from skills.base import BaseSkill, SkillManifest
from backend.tools import FilesystemTool


class FilesystemSkill(BaseSkill):
    def __init__(self, workspace_root: Path):
        manifest = SkillManifest(
            name="filesystem",
            version="1.0.0",
            description="Sandboxed file management and inspection.",
            capabilities=["list_dir", "read_file", "write_file", "search_files", "file_info"],
            required_tools=["filesystem"],
            permissions_required=[0, 1]
        )
        super().__init__(manifest)
        self.tool = FilesystemTool(workspace_root)

    async def initialize(self) -> bool:
        return True

    def get_tools(self) -> List[Any]:
        return [self.tool]

    async def execute_capability(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        p = dict(params)
        p["action"] = capability
        res = await self.tool.execute(p)
        return {"success": res.success, "output": res.output, "error": res.error}
