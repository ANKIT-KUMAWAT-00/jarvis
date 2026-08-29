"""
JARVIS Main Application Server
FastAPI backend providing REST endpoints, WebSockets for live telemetry,
and static frontend serving.
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("jarvis.server")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import config, PROJECT_ROOT, FRONTEND_DIR, DATA_DIR, LOGS_DIR
from backend.security import PermissionEngine, ActionLevel, ConfirmationToken, Sanitizer
from backend.memory import MemoryStore, MemoryItem, MemoryRetriever, KnowledgeGraphBuilder
from backend.tools import (
    ToolRegistry, FilesystemTool, TerminalTool, ProcessTool,
    GitTool, ScreenVisionTool, BrowserTool, SystemInfoTool,
    AppControlTool, MeetingSchedulerTool, CommunicationTool
)
from backend.providers import LLMProvider, GeminiProvider, MockProvider
from backend.agent import JarvisAgent
from backend.tasks import TaskScheduler
from skills.base import SkillRegistry
from skills.coding.skill import CodingSkill
from skills.filesystem.skill import FilesystemSkill
from skills.browser.skill import BrowserSkill
from skills.vision.skill import VisionSkill
from skills.reminders.skill import RemindersSkill
from skills.custom.skill import CustomSkill


# Global singletons
permission_engine = PermissionEngine()
memory_store = MemoryStore(config.db_path)
graph_builder = KnowledgeGraphBuilder(config.notes_dir, memory_store)
task_scheduler = TaskScheduler(memory_store)

# Initialize Tools
tool_registry = ToolRegistry(permission_engine, memory_store)
tool_registry.register(FilesystemTool(config.workspace_root))
tool_registry.register(TerminalTool(config.workspace_root))
tool_registry.register(ProcessTool(LOGS_DIR))
tool_registry.register(GitTool(config.workspace_root))
tool_registry.register(ScreenVisionTool(DATA_DIR / "scratch"))
tool_registry.register(BrowserTool())
tool_registry.register(SystemInfoTool())
