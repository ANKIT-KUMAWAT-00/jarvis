"""
JARVIS Autonomous Agent Core
Coordinates Intent Understanding -> Planning -> Safety Check -> Execution ->
Observation -> Verification -> Memory Update -> Truthful Response.
"""

import asyncio
import os
import time
from typing import Dict, Any, Optional, List, Callable
from backend.config import JarvisConfig
from backend.providers.base import LLMProvider, PlanResult, PlanStep
from backend.tools.registry import ToolRegistry
from backend.tools.base import ToolResult, VerificationResult
from backend.tools.app_control import AppControlTool
from backend.memory.store import MemoryStore, MemoryItem
from backend.memory.search import MemoryRetriever
from backend.security.permissions import ActionLevel, ConfirmationToken
from .planner import IntentClassifier, Planner
from .verification import VerificationEngine
from .self_repair import SelfRepairEngine
from backend.context.context_manager import ContextManager, EntityReference
from backend.capabilities.registry import CapabilityRegistry
from backend.observer.environment_observer import EnvironmentObserver
