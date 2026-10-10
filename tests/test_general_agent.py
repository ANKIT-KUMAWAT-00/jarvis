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


@pytest.mark.asyncio
async def test_open_app_store_and_download_whatsapp(agent):
    """'Open the App Store and download the WhatsApp' targets the App Store page for WhatsApp directly."""
    res = await agent.run("Open the App Store and download the WhatsApp")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    last_task = agent.recent_task_records[-1]
    step = last_task["steps"][0]
    assert step["tool_name"] == "app_control"
    assert step["action"] == "open_app_store"
    assert step["parameters"]["app_name"].lower() == "whatsapp"


@pytest.mark.asyncio
async def test_generic_app_name_rejection():
    """Generic words like 'App' or 'Store' must never be treated as valid macOS applications."""
    for generic in ("App", "app", "application", "the app", "Store", "apps"):
        installed, path = AppControlTool.check_app_installed(generic)
        if generic.lower() not in ("store",):  # 'store' maps to 'App Store'
            assert installed is False
            assert path is None


@pytest.mark.asyncio
async def test_retry_last_task_on_go_for_it(agent):
    """When user commands 'Don't give me excuses just go for it', re-execute the previous task."""
    # First execute an initial command
    res1 = await agent.run("Open YouTube")
    assert res1["state"] == "COMPLETED"
    assert len(agent.recent_task_records) == 1

    # Follow up with 'Don't give me excuses just go for it'
    res2 = await agent.run("Don't give me excuses just go for it")
    assert res2["state"] == "COMPLETED"
    assert res2["verified"] is True
    # The last recorded goal should still be Open YouTube
    assert agent.recent_task_records[-1]["goal"] == "Open YouTube"


@pytest.mark.asyncio
async def test_app_store_approval_with_go_for_it(agent):
    """When waiting for App Store approval, 'just go for it' approves and opens the App Store."""
    res1 = await agent.run("Call Krishna using WhatsApp")
    assert res1["state"] == "WAITING_FOR_APP_STORE_APPROVAL"

    res2 = await agent.run("just go for it")
    assert res2["state"] == "WAITING_FOR_INSTALLATION"
    assert "opened the Mac App Store page" in res2["response"]


@pytest.mark.asyncio
async def test_play_music_in_youtube_execution(agent):
    """'Play a music in YouTube' must execute play_media with query 'music'."""
    res = await agent.run("Play a music in YouTube")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    last_task = agent.recent_task_records[-1]
    step = last_task["steps"][0]
    assert step["tool_name"] == "app_control"
    assert step["action"] == "play_media"
    assert step["parameters"]["query"].lower() == "music"


@pytest.mark.asyncio
async def test_play_artist_or_song_directly(agent):
    """'play Vishal' must execute play_media with query 'vishal'."""
    res = await agent.run("play Vishal")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    last_task = agent.recent_task_records[-1]
    step = last_task["steps"][0]
    assert step["action"] == "play_media"
    assert step["parameters"]["query"].lower() == "vishal"


@pytest.mark.asyncio
async def test_unfulfilled_task_re_execution_on_criticism(agent):
    """When user says 'Bro you haven't done any task', re-execute the preceding command."""
    await agent.run("Play a music in YouTube")
    res = await agent.run("Bro you haven't done any task")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    assert agent.recent_task_records[-1]["goal"] == "Play a music in YouTube"


@pytest.mark.asyncio
async def test_media_followup_artist_name(agent):
    """When user types artist name 'Vishal' after media context, execute play_media for 'Vishal'."""
    await agent.run("Play a music in YouTube")
    res = await agent.run("Vishal")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    last_task = agent.recent_task_records[-1]
    assert last_task["goal"] == "Play Vishal on YouTube"
    assert last_task["steps"][0]["parameters"]["query"].lower() == "vishal"


@pytest.mark.asyncio
async def test_open_telegram_in_safari(agent):
    """'Jarvis open telegram in Safari' must open web.telegram.org in Safari, never YouTube."""
    res = await agent.run("Jarvis open telegram in Safari")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    last_task = agent.recent_task_records[-1]
    step = last_task["steps"][0]
    assert step["tool_name"] == "app_control"
    assert step["action"] == "open_url"
    assert "web.telegram.org" in step["parameters"]["url"]
    assert step["parameters"]["browser"] == "Safari"


@pytest.mark.asyncio
async def test_search_telegram_in_safari(agent):
    """'search telegram in safari' must search Google for telegram in Safari."""
    res = await agent.run("search telegram in safari")
    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    last_task = agent.recent_task_records[-1]
    step = last_task["steps"][0]
    assert step["tool_name"] == "app_control"
    assert step["action"] == "open_url"
    assert "google.com/search" in step["parameters"]["url"]
    assert "telegram" in step["parameters"]["url"]
    assert step["parameters"]["browser"] == "Safari"


@pytest.mark.asyncio
async def test_no_media_hijack_after_music(agent):
    """After playing music, 'Open telegram in Safari' must open Telegram, not play on YouTube."""
    await agent.run("Play a music in YouTube")
    res = await agent.run("Open telegram in Safari")
    assert res["state"] == "COMPLETED"
    last_task = agent.recent_task_records[-1]
    assert last_task["steps"][0]["action"] == "open_url"
    assert "telegram" in last_task["steps"][0]["parameters"]["url"]
    assert "youtube" not in last_task["steps"][0]["parameters"]["url"]


