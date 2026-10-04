"""
JARVIS Extensible Skill Architecture
Defines base interfaces, manifest schemas, and registry for modular capabilities.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path


class SkillManifest(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str
    author: str = "JARVIS Core"
    capabilities: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    permissions_required: List[int] = Field(default_factory=list)
    is_enabled: bool = True
    config_schema: Dict[str, Any] = Field(default_factory=dict)


class BaseSkill(ABC):
    """Abstract base class for all modular JARVIS skills."""

    def __init__(self, manifest: SkillManifest):
        self.manifest = manifest

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize skill resources and check prerequisites."""
        pass

    @abstractmethod
    def get_tools(self) -> List[Any]:
        """Return list of tool instances provided or utilized by this skill."""
        pass

    @abstractmethod
    async def execute_capability(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Directly invoke a skill capability."""
        pass


class SkillRegistry:
    """Discovers, loads, and manages JARVIS skills."""

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill):
        self._skills[skill.manifest.name] = skill

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)

    def list_skills(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": s.manifest.name,
                "version": s.manifest.version,
                "description": s.manifest.description,
                "capabilities": s.manifest.capabilities,
                "tools": s.manifest.required_tools,
                "enabled": s.manifest.is_enabled
            }
            for s in self._skills.values()
        ]
