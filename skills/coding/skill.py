"""
JARVIS Coding Skill
Orchestrates codebase inspection, dependency checking, linting, tests, and Git integration.
"""

from typing import List, Dict, Any
from pathlib import Path
from skills.base import BaseSkill, SkillManifest
from backend.tools import FilesystemTool, TerminalTool, GitTool


class CodingSkill(BaseSkill):
    def __init__(self, workspace_root: Path):
        manifest = SkillManifest(
            name="coding",
            version="1.0.0",
            description="Codebase inspection, linting, test execution, and safe refactoring.",
            capabilities=["inspect_codebase", "run_tests", "execute_lint", "git_status"],
            required_tools=["filesystem", "terminal", "git"],
            permissions_required=[0, 1]
        )
        super().__init__(manifest)
        self.workspace_root = workspace_root
        self.fs_tool = FilesystemTool(workspace_root)
        self.term_tool = TerminalTool(workspace_root)
        self.git_tool = GitTool(workspace_root)

    async def initialize(self) -> bool:
        return self.workspace_root.exists()

    def get_tools(self) -> List[Any]:
        return [self.fs_tool, self.term_tool, self.git_tool]

    async def execute_capability(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if capability == "git_status":
            res = await self.git_tool.execute({"action": "status"})
            return {"success": res.success, "output": res.output, "error": res.error}
        elif capability == "run_tests":
            cmd = params.get("command", "pytest")
            res = await self.term_tool.execute({"command": cmd, "timeout": 30.0})
            return {"success": res.success, "output": res.output, "error": res.error}
        elif capability == "inspect_codebase":
            res = await self.fs_tool.execute({"action": "list_dir", "path": params.get("path", ".")})
            return {"success": res.success, "output": res.output, "error": res.error}
        else:
            return {"success": False, "error": f"Unknown capability '{capability}'"}
