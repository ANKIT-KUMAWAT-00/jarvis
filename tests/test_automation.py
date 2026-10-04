"""
Tests for JARVIS macOS Automation:
Application Control, Meeting Scheduling, Timers, and Communication.
"""

import pytest
from pathlib import Path
from backend.tools.app_control import AppControlTool
from backend.tools.meeting_scheduler import MeetingSchedulerTool
from backend.tools.communication import CommunicationTool
from backend.agent.planner import IntentClassifier
from backend.agent.core import JarvisAgent
from backend.tools.registry import ToolRegistry
from backend.security.permissions import PermissionEngine
from backend.memory.store import MemoryStore
from backend.providers.mock import MockProvider
from backend.config import JarvisConfig


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


@pytest.mark.asyncio
async def test_app_control_tool_listing():
    tool = AppControlTool()
    assert tool.name == "app_control"
    res = await tool.execute({"action": "list_apps"})
    assert res.success is True
    assert "Calculator" in res.output["supported_common_apps"]


@pytest.mark.asyncio
async def test_meeting_scheduler_create_meeting(temp_dir):
    tool = MeetingSchedulerTool(data_dir=temp_dir)
    assert tool.name == "meeting_scheduler"
    res = await tool.execute({
        "action": "create_meeting",
        "title": "Quarterly Strategy Review",
        "date": "Tomorrow",
        "time": "2:00 PM",
        "duration_minutes": 45
    })
    assert res.success is True
    assert "meeting_id" in res.raw_data
    assert "meet.google.com" in res.raw_data["url"]
    assert Path(res.raw_data["ics"]).exists()


@pytest.mark.asyncio
async def test_meeting_scheduler_set_timer(temp_dir):
    tool = MeetingSchedulerTool(data_dir=temp_dir)
    res = await tool.execute({
        "action": "set_timer",
        "seconds": 1,
        "label": "Coffee Break"
    })
    assert res.success is True
    assert res.raw_data["duration_seconds"] == 1


@pytest.mark.asyncio
async def test_communication_send_email():
    tool = CommunicationTool()
    assert tool.name == "communication"
    res = await tool.execute({
        "action": "send_email",
        "to": "alex@example.com",
        "subject": "Status Report",
        "body": "All systems operational."
    })
    assert res.success is True
    assert res.raw_data["to"] == "alex@example.com"
    assert res.raw_data["sent"] is True


@pytest.mark.asyncio
async def test_communication_send_message():
    tool = CommunicationTool()
    res = await tool.execute({
        "action": "send_message",
        "to": "+15551234567",
        "message": "JARVIS ready for deployment."
    })
    assert res.success is True
    assert res.raw_data["to"] == "+15551234567"
    assert res.raw_data["dispatched"] is True


def test_intent_classification_for_commands():
    assert IntentClassifier.classify("open Calculator") == "ACTIONABLE_COMMAND"
    assert IntentClassifier.classify("launch Safari") == "ACTIONABLE_COMMAND"
    assert IntentClassifier.classify("fix a meeting for tomorrow at 3pm") == "ACTIONABLE_COMMAND"
    assert IntentClassifier.classify("schedule a team call next Monday") == "ACTIONABLE_COMMAND"
    assert IntentClassifier.classify("set a timer for 10 minutes") == "ACTIONABLE_COMMAND"
    assert IntentClassifier.classify("send an email to test@example.com") == "ACTIONABLE_COMMAND"
    assert IntentClassifier.classify("send a message to John") == "ACTIONABLE_COMMAND"


@pytest.mark.asyncio
async def test_agent_open_app_workflow(temp_dir):
    config = JarvisConfig(workspace_root=temp_dir)
    pe = PermissionEngine()
    store = MemoryStore(temp_dir / "test.db")
    tr = ToolRegistry(pe, store)
    tr.register(AppControlTool())
    provider = MockProvider()

    agent = JarvisAgent(config=config, provider=provider, tool_registry=tr, memory_store=store)
    result = await agent.run("open calculator")
    assert result["state"] == "COMPLETED"
    assert result["verified"] is True
    assert any("Calculator" in r for r in result["receipts"])


@pytest.mark.asyncio
async def test_agent_meeting_workflow(temp_dir):
    config = JarvisConfig(workspace_root=temp_dir)
    pe = PermissionEngine()
    store = MemoryStore(temp_dir / "test.db")
    tr = ToolRegistry(pe, store)
    tr.register(MeetingSchedulerTool(data_dir=temp_dir))
    provider = MockProvider()

    agent = JarvisAgent(config=config, provider=provider, tool_registry=tr, memory_store=store)
    result = await agent.run("fix a meeting for tomorrow")
    assert result["state"] == "COMPLETED"
    assert result["verified"] is True
    assert any("meeting" in r.lower() or "meet" in r.lower() for r in result["receipts"])
