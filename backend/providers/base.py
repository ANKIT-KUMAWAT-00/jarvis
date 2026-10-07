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


class PlanResult(BaseModel):
    goal: str
    intent: str
    requires_tools: bool
    summary: str
    steps: List[PlanStep] = Field(default_factory=list)
    verification_criteria: str
    task_object: Optional[TaskObject] = None



class LLMProvider(ABC):
    """Abstract interface that all LLM backends must implement."""

    @abstractmethod
    def get_model_name(self) -> str:
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Conversational chat endpoint."""
        pass

    @abstractmethod
    async def plan(
        self,
        goal: str,
        context: Optional[str] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None
    ) -> PlanResult:
        """Structured plan generation for multi-step tasks."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema_class: Type[BaseModel],
        system_instruction: Optional[str] = None
    ) -> BaseModel:
        """Generate machine-readable responses strictly matching a Pydantic schema."""
        pass

    @abstractmethod
    async def analyze(
        self,
        content: str,
        instruction: str,
        is_untrusted: bool = True,
        image_base64: Optional[str] = None
    ) -> str:
        """Analyze text or multimodal image content."""
        pass
