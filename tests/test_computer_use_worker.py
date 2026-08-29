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
async def test_worker_spotify_and_play_playlist(agent):
    """
    'Open Spotify and play my playlist'
    Must open Spotify AND play the requested playlist.
    """
    AppControlTool.TEST_INSTALLED_APPS.add("spotify")
    try:
        res = await agent.run("Open Spotify and play my chill vibes playlist")
        assert res["state"] == "COMPLETED"
        assert res["verified"] is True

        last_task = agent.recent_task_records[-1]
        steps = last_task["steps"]
        assert len(steps) == 2

        # Step 1: Open Spotify
        assert steps[0]["action"] == "open_app"
        assert steps[0]["parameters"]["app_name"] == "Spotify"

        # Step 2: Play media
        assert steps[1]["action"] == "play_media"
        assert "chill vibes" in steps[1]["parameters"]["query"].lower()
    finally:
        AppControlTool.TEST_INSTALLED_APPS.discard("spotify")


@pytest.mark.asyncio
async def test_worker_gmail_and_send_email(agent):
    """
    'Open Gmail and send this email'
    Must open Gmail AND send the email.
    """
    res = await agent.run("Open Gmail and send this email to test@example.com")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True

    last_task = agent.recent_task_records[-1]
    steps = last_task["steps"]
    assert len(steps) == 2

    # Step 1: Open Gmail
    assert steps[0]["action"] == "open_url"
    assert "mail.google.com" in steps[0]["parameters"]["url"]

    # Step 2: Send email
    assert steps[1]["tool_name"] == "communication"
    assert steps[1]["action"] == "send_email"
    assert steps[1]["parameters"]["to"] == "test@example.com"


# ==============================================================================
# 2. CONTEXT MANAGER & MULTI-TURN REFERENCE RESOLUTION
# ==============================================================================

@pytest.mark.asyncio
async def test_anaphoric_reference_resolution_run_it(agent):
    """
    Turn 1: 'Open VS Code and open my ResumeIQ project'
    Turn 2: 'Run it'
    JARVIS must understand 'it' refers to the ResumeIQ project from turn 1.
    """
    AppControlTool.TEST_INSTALLED_APPS.add("visual studio code")
    try:
        # Turn 1
        res1 = await agent.run("Open my ResumeIQ project")
        assert res1["state"] == "COMPLETED"
        assert agent.context_manager.context.active_project == "ResumeIQ"

        # Turn 2: 'Run it'
        res2 = await agent.run("Run it")
        assert res2["state"] == "COMPLETED"
        assert res2["verified"] is True

        last_task = agent.recent_task_records[-1]
        assert "ResumeIQ" in str(last_task)
    finally:
        AppControlTool.TEST_INSTALLED_APPS.discard("visual studio code")


@pytest.mark.asyncio
async def test_contextual_app_resolution_spotify_playlist(agent):
    """
    Turn 1: 'Open Spotify'
    Turn 2: 'Play my workout playlist'
    JARVIS must understand second command refers to Spotify without repeating the app name.
    """
    AppControlTool.TEST_INSTALLED_APPS.add("spotify")
    try:
        # Turn 1: Open Spotify
        res1 = await agent.run("Open Spotify")
        assert res1["state"] == "COMPLETED"
        assert agent.context_manager.context.current_app == "Spotify"

        # Turn 2: 'Play my workout playlist'
        res2 = await agent.run("Play my workout playlist")
        assert res2["state"] == "COMPLETED"
        assert res2["verified"] is True

        last_task = agent.recent_task_records[-1]
        assert any(s["tool_name"] == "app_control" and s["action"] == "play_media" for s in last_task["steps"])
    finally:
        AppControlTool.TEST_INSTALLED_APPS.discard("spotify")


@pytest.mark.asyncio
async def test_contextual_person_resolution_send_her_message(agent):
    """
    Turn 1: 'Call Krishna' (or mention Krishna)
    Turn 2: 'Send her that I will call later'
    JARVIS must resolve 'her' to Krishna.
    """
    res1 = await agent.run("Call Krishna")
    assert res1["state"] == "COMPLETED"
    assert "Krishna" in agent.context_manager.context.recent_people

    # Turn 2: Pronoun resolution for 'her'
    res2 = await agent.run("Send her that I will call later")
    assert res2["state"] == "COMPLETED"
    last_task = agent.recent_task_records[-1]
    assert last_task["steps"][0]["parameters"]["to"] == "Krishna"


@pytest.mark.asyncio
async def test_ordinal_reference_resolution(agent):
    """
    Ordinal resolution:
    Given recent results, 'Play the second playlist' and 'Open the first one'
    must resolve to the correct items.
    """
    agent.context_manager.set_recent_results(["Focus Daily", "High Energy Workout", "Ambient Study"])

    ref1 = agent.context_manager.resolve_references("Play the second playlist")
    assert ref1["resolved_entities"]["selected_item"] == "High Energy Workout"
    assert "'High Energy Workout'" in ref1["resolved_prompt"]

    ref2 = agent.context_manager.resolve_references("Open the first one")
    assert ref2["resolved_entities"]["selected_item"] == "Focus Daily"
    assert "'Focus Daily'" in ref2["resolved_prompt"]


# ==============================================================================
# 3. TASK STATE SURVIVAL & 'CONTINUE' RESUMPTION
# ==============================================================================

@pytest.mark.asyncio
async def test_task_state_resumption_on_continue(agent):
    """
    When a task is paused awaiting permission, saying 'continue'
    must retrieve the pending task and resume execution cleanly.
    """
    # Simulate a paused task waiting for permission
    agent.task_state_manager.start_task(
        "Open Safari and search for documentation",
        agent.planner.create_plan.__wrapped__("Open Safari", available_tools=[]) if hasattr(agent.planner.create_plan, "__wrapped__") else None or
        await agent.planner.create_plan("Open Safari", available_tools=agent.tool_registry.list_tools())
    )
    agent.task_state_manager.pause_for_permission("accessibility", "Accessibility permission needed")
    agent.pending_task = {
        "type": "MAC_PERMISSION",
        "original_goal": "Open Safari and search for documentation",
        "waiting_for": "permission_grant"
    }

    # User says 'continue'
    res = await agent.run("continue")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    assert agent.pending_task is None


# ==============================================================================
# 4. CAPABILITY REGISTRY & ACTION ABSTRACTION
# ==============================================================================

def test_capability_registry_discovery():
    """Verify CapabilityRegistry dynamically discovers installed and browser-accessible applications."""
    registry = CapabilityRegistry()
    profile = registry.get_profile("Safari")
    assert profile.name == "safari"
    assert "browser" in profile.interfaces
    assert "navigate" in profile.capabilities

    method_info = registry.discover_app("Safari")
    assert method_info["available"] is True
    assert method_info["method"] in ("native_api", "applescript", "accessibility")

    # Uninstalled app discovery
    uninstalled_info = registry.discover_app("NonExistentCustomAppXYZ")
    assert uninstalled_info["available"] is False
    assert uninstalled_info["method"] == "app_store"


@pytest.mark.asyncio
async def test_action_engine_execution():
    """Verify ActionEngine dispatches high-level actions across underlying controllers."""
    engine = ActionEngine()
    # Test open URL via browser/macOS controller
    res = await engine.execute_action("open_url", {"url": "https://example.com", "browser": "Safari"})
    assert res.success is True
    assert "example.com" in res.raw_data.get("url", "")


# ==============================================================================
# 5. INSTALLATION INTEGRITY & PREVENTING FALSE COMPLETION
# ==============================================================================

@pytest.mark.asyncio
async def test_app_store_installation_integrity_and_resumption(agent: JarvisAgent):
    """
    Verify:
    1. Opening App Store does NOT claim false completion when an app is not installed.
    2. User saying 'Now you need to install it I have given you all the access' triggers install action without false success.
    3. Resumes original goal once user completes installation.
    """
    # 1. User wants to contact someone on WhatsApp (WhatsApp is not installed in test by default)
    res1 = await agent.run("Open WhatsApp and message Krishna that I will call later")
    assert res1["state"] == "WAITING_FOR_APP_STORE_APPROVAL"
    assert "WhatsApp" in res1["response"]
    assert agent.pending_task is not None
    assert agent.pending_task["waiting_for"] == "app_store_approval"

    # 2. User approves opening the App Store
    res2 = await agent.run("yes please open it")
    assert res2["state"] == "WAITING_FOR_INSTALLATION"
    assert agent.pending_task is not None
    assert agent.pending_task["waiting_for"] == "installation_complete"
    assert "Please install it" in res2["response"]

    # 3. User says "Now you need to install it I have given you all the access"
    res3 = await agent.run("Now you need to install it I have given you all the access")
    assert res3["state"] == "WAITING_FOR_INSTALLATION"
    assert res3["verified"] is False
    assert agent.pending_task is not None
    assert "initiated installation" in res3["response"] or "Mac App Store" in res3["response"]

    # 4. User reports finished / continue after completing installation
    AppControlTool.TEST_INSTALLED_APPS.add("whatsapp")
    try:
        res4 = await agent.run("done, I have installed it")
        assert res4["state"] == "COMPLETED"
        assert res4["verified"] is True
        assert agent.pending_task is None
    finally:
        AppControlTool.TEST_INSTALLED_APPS.discard("whatsapp")


def test_agent_is_running_property(agent: JarvisAgent):
    """Verify is_running correctly reflects active task execution state."""
    assert agent.is_running is False

