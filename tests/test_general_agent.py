"""
Tests for JARVIS General-Purpose Intelligent Mac Computer Agent.
Validates:
1. Zero hardcoded assumptions (no auto song playing on 'Open YouTube').
2. User instruction depth matching (open vs search vs play).
3. Application discovery & Mac App Store fallback for uninstalled applications.
4. Capability-based contact calling (FaceTime vs explicit WhatsApp).
5. macOS Permission Escalation System (automatic System Settings navigation and task persistence).
6. Structured TaskObject generation.
7. Project opening in editor.
"""

import pytest
import os
from backend.config import JarvisConfig
from backend.providers.mock import MockProvider
from backend.tools.registry import ToolRegistry
from backend.tools.app_control import AppControlTool
from backend.tools.communication import CommunicationTool
from backend.memory.store import MemoryStore
import tempfile
from pathlib import Path
from backend.security.permissions import PermissionEngine
from backend.agent.core import JarvisAgent


@pytest.fixture
def agent():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        db_path = workspace / "test_memory.db"
        notes_dir = workspace / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        config = JarvisConfig(workspace_root=workspace, notes_dir=notes_dir, db_path=db_path)
        provider = MockProvider()
        mem_store = MemoryStore(db_path)
        perm_engine = PermissionEngine()
        tools = ToolRegistry(perm_engine, mem_store)
        tools.register(AppControlTool())
        tools.register(CommunicationTool())
        yield JarvisAgent(config=config, provider=provider, tool_registry=tools, memory_store=mem_store)


@pytest.mark.asyncio
