"""
Comprehensive Tests for JARVIS Universal Computer-Use Worker Architecture.
Validates:
1. Universal Computer-Use Behavior:
   - 'Open WhatsApp and open Krishna's chat' (worker does not stop after opening WhatsApp)
   - 'Open Safari and search for something'
   - 'Open VS Code and run my project'
   - 'Open Spotify and play my playlist'
   - 'Open Gmail and send this email'
2. Context Manager & Multi-Turn Reference Resolution:
   - 'Open VS Code and open my ResumeIQ project' -> 'Run it'
   - 'Open Spotify' -> 'Play my workout playlist'
   - 'Open WhatsApp in Safari' -> 'Open Krishna's chat'
   - 'Open WhatsApp and message Krishna' -> 'Send her this message'
3. Ordinal Reference Resolution:
   - 'Play the second playlist' / 'Open the first one'
4. Task State Survival across Pauses & 'Continue' Resumption:
   - Preserves pending subtasks; resumes on 'continue'
5. Verification Integrity:
   - Opening an app is not task completion; never claims false success on partial completion
6. Capability Registry & Action Abstraction:
   - Non-hardcoded capability discovery and layer selection
"""

import pytest
import tempfile
from pathlib import Path
from backend.config import JarvisConfig
from backend.providers.mock import MockProvider
from backend.tools.registry import ToolRegistry
from backend.tools.app_control import AppControlTool
from backend.tools.communication import CommunicationTool
from backend.tools.terminal import TerminalTool
from backend.memory.store import MemoryStore
from backend.security.permissions import PermissionEngine
from backend.agent.core import JarvisAgent
from backend.capabilities.registry import CapabilityRegistry
from backend.actions.action_engine import ActionEngine
from backend.context.context_manager import ContextManager


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
        tools.register(TerminalTool(default_cwd=workspace))
        yield JarvisAgent(config=config, provider=provider, tool_registry=tools, memory_store=mem_store)


# ==============================================================================
# 1. CORE UNIVERSAL WORKER BEHAVIOR ACROSS MULTIPLE APPLICATIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_worker_whatsapp_and_open_chat(agent):
    """
    JARVIS acts as worker: 'Open WhatsApp and open Krishna's chat'
    Worker must NOT stop after launching WhatsApp. It must open the chat and verify completion.
    """
    AppControlTool.TEST_INSTALLED_APPS.add("whatsapp")
    try:
        res = await agent.run("Open WhatsApp and open Krishna's chat")
        assert res["state"] == "COMPLETED"
        assert res["verified"] is True

        last_task = agent.recent_task_records[-1]
        steps = last_task["steps"]
        assert len(steps) >= 2

        # Step 1: Open WhatsApp
        assert steps[0]["tool_name"] == "app_control"
        assert steps[0]["action"] == "open_app"
        assert steps[0]["parameters"]["app_name"] == "WhatsApp"

        # Step 2: In-app interaction (open chat)
        assert steps[1]["action"] == "interact_web"
        assert steps[1]["parameters"]["target"] == "Krishna"
    finally:
        AppControlTool.TEST_INSTALLED_APPS.discard("whatsapp")


@pytest.mark.asyncio
async def test_worker_safari_and_search(agent):
    """'Open Safari and search for something' must navigate and perform the search query."""
    res = await agent.run("Open Safari and search for quantum computing")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True

    last_task = agent.recent_task_records[-1]
    step = last_task["steps"][0]
    assert step["action"] == "open_url"
    assert "google.com/search" in step["parameters"]["url"]
    assert "quantum" in step["parameters"]["url"]


@pytest.mark.asyncio
async def test_worker_vscode_and_run_project(agent):
    """
    'Open VS Code and run my project'
    Must open editor AND execute the runtime via terminal.
    """
    AppControlTool.TEST_INSTALLED_APPS.add("visual studio code")
    try:
        res = await agent.run("Open VS Code and run my ResumeIQ project")
        assert res["state"] == "COMPLETED"
        assert res["verified"] is True

        last_task = agent.recent_task_records[-1]
        steps = last_task["steps"]
        assert len(steps) == 2

        # Step 1: Open project in VS Code
        assert steps[0]["tool_name"] == "app_control"
        assert steps[0]["action"] == "open_project"
        assert "resumeiq" in steps[0]["parameters"]["project_name"].lower()

        # Step 2: Run project in terminal
        assert steps[1]["tool_name"] == "terminal"
        assert steps[1]["action"] == "run_command"
        assert "resumeiq" in steps[1]["parameters"]["command"].lower()
    finally:
        AppControlTool.TEST_INSTALLED_APPS.discard("visual studio code")


@pytest.mark.asyncio
