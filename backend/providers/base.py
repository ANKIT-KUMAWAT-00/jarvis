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


