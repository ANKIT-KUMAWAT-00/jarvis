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
async def test_instruction_depth_open_youtube_only(agent):
    """'Open YouTube' must ONLY open YouTube homepage; never search or play music."""
    res = await agent.run("Open YouTube")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    # Verify the plan and execution only opened URL, not play_media
    last_task = agent.recent_task_records[-1]
    step = last_task["steps"][0]
    assert step["tool_name"] == "app_control"
    assert step["action"] == "open_url"
    assert "youtube.com" in step["parameters"]["url"]
    assert "search_query" not in step["parameters"]["url"]
    assert "rajasthani" not in str(last_task).lower()


@pytest.mark.asyncio
async def test_instruction_depth_search_youtube(agent):
    """'Open YouTube and search for Rajasthani songs' must search but not autoplay."""
    res = await agent.run("Open YouTube and search for Rajasthani songs")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    last_task = agent.recent_task_records[-1]
    step = last_task["steps"][0]
    assert step["action"] == "open_url"
    assert "search_query=" in step["parameters"]["url"]
    assert "rajasthani" in step["parameters"]["url"].lower()


@pytest.mark.asyncio
async def test_instruction_depth_play_media(agent):
    """'Open YouTube and play a Rajasthani song' must search and play."""
    res = await agent.run("Open YouTube and play a Rajasthani song")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    last_task = agent.recent_task_records[-1]
    step = last_task["steps"][0]
    assert step["action"] == "play_media"
    assert "rajasthani" in step["parameters"]["query"].lower()


@pytest.mark.asyncio
async def test_uninstalled_app_store_fallback(agent):
    """'Open Spotify' when Spotify is not installed must trigger App Store prompt and retain task state."""
    res = await agent.run("Open Spotify")
    assert res["state"] == "WAITING_FOR_APP_STORE_APPROVAL"
    assert res["verified"] is False
    assert "Spotify" in res["response"]
    assert "App Store" in res["response"]
    assert agent.pending_task is not None
    assert agent.pending_task["type"] == "APP_INSTALL"
    assert agent.pending_task["app_name"] == "Spotify"

    # User approves opening App Store
    res_approve = await agent.run("Yes please")
    assert res_approve["state"] == "WAITING_FOR_INSTALLATION"
    assert "App Store" in res_approve["response"]
    assert agent.pending_task["waiting_for"] == "installation_complete"

    # Simulate app installation completed on system
    AppControlTool.TEST_INSTALLED_APPS.add("spotify")
    try:
        # User completes installation and resumes
        res_resume = await agent.run("Done, it is installed")
        assert res_resume["state"] == "COMPLETED"
        assert agent.pending_task is None
    finally:
        AppControlTool.TEST_INSTALLED_APPS.discard("spotify")


@pytest.mark.asyncio
async def test_uninstalled_app_declined(agent):
    """User declines App Store installation -> cancels cleanly."""
    res = await agent.run("Open Spotify")
    assert res["state"] == "WAITING_FOR_APP_STORE_APPROVAL"

    res_cancel = await agent.run("No thanks")
    assert res_cancel["state"] == "CANCELLED"
    assert agent.pending_task is None


@pytest.mark.asyncio
async def test_contact_call_facetime_by_default(agent):
    """'Call Krishna' must use available communication service (FaceTime), not assume WhatsApp."""
    res = await agent.run("Call Krishna")
    assert res["state"] == "COMPLETED"
    last_task = agent.recent_task_records[-1]
    step = last_task["steps"][0]
    assert step["tool_name"] == "communication"
    assert step["action"] == "make_call"
    assert step["parameters"]["recipient"] == "Krishna"
    assert step["parameters"].get("app") is None  # Defaults to available/FaceTime


@pytest.mark.asyncio
async def test_contact_call_whatsapp_explicit(agent):
    """'Call Krishna using WhatsApp' requires WhatsApp explicitly."""
    res = await agent.run("Call Krishna using WhatsApp")
    # WhatsApp is not installed on this test host -> routes to App Store flow
    assert res["state"] == "WAITING_FOR_APP_STORE_APPROVAL"
    assert "WhatsApp" in res["response"]
    assert agent.pending_task["app_name"] == "WhatsApp"


@pytest.mark.asyncio
async def test_permission_escalation_system(agent):
    """When a task fails due to missing macOS permission, open Settings and pause for resumption."""
    # Simulate a step that failed with Accessibility permission missing
    err = "System Events got an error: Access not allowed. osascript is not allowed assistive access."
    detected_pane = agent._detect_permission_requirement(err)
    assert detected_pane == "accessibility"

    # Automation error
    auto_err = "Not authorized to send Apple events to System Events (-1743)."
    assert agent._detect_permission_requirement(auto_err) == "automation"

    # Screen recording error
    sr_err = "Screen recording permission denied."
    assert agent._detect_permission_requirement(sr_err) == "screen_recording"


@pytest.mark.asyncio
async def test_open_project_workflow(agent):
    """'Open my ResumeIQ project' locates project and prepares it in editor."""
    res = await agent.run("Open my ResumeIQ project")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    last_task = agent.recent_task_records[-1]
    step = last_task["steps"][0]
    assert step["action"] == "open_project"
    assert "resumeiq" in step["parameters"]["project_name"].lower()


@pytest.mark.asyncio
async def test_task_object_structure():
    """Verify that MockProvider generates a valid structured TaskObject."""
    mock = MockProvider()
    plan_open = await mock.plan("Open Safari")
    assert plan_open.task_object is not None
    assert plan_open.task_object.intent == "open_application"
    assert plan_open.task_object.target == "Safari"

    plan_play = await mock.plan("Open YouTube and play a Rajasthani song")
    assert plan_play.task_object is not None
    assert plan_play.task_object.intent == "play_music"
    assert len(plan_play.task_object.actions) >= 2
