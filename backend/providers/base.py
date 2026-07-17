"""
JARVIS LLM Provider Abstraction
Decouples agent logic from specific model providers (Gemini, Mock, Future).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    step_id: int
    title: str
    tool_name: str
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str
    risk_level: int = 1


class TaskAction(BaseModel):
    type: str
    target: Optional[str] = None
    query: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class TaskDependency(BaseModel):
    type: str  # application_installed, macos_permission, network
    name: str  # Spotify, Accessibility, etc.
    resolved: bool = False
    resolution_path: Optional[str] = None


class TaskObject(BaseModel):
    intent: str
    target: str
    actions: List[TaskAction] = Field(default_factory=list)
    dependencies: List[TaskDependency] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    status: str = "pending"


