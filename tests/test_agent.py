"""
Integration tests for JARVIS Agent core loop, intent routing, and execution.
"""

import pytest
import tempfile
from pathlib import Path
from backend.config import JarvisConfig
from backend.providers.mock import MockProvider
from backend.tools.registry import ToolRegistry
from backend.tools.filesystem import FilesystemTool
from backend.tools.terminal import TerminalTool
from backend.memory.store import MemoryStore
from backend.security.permissions import PermissionEngine
from backend.agent.core import JarvisAgent
from backend.agent.planner import IntentClassifier


@pytest.fixture
def agent_environment():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        db_path = workspace / "test_memory.db"
        notes_dir = workspace / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)

        config = JarvisConfig(
            workspace_root=workspace,
            notes_dir=notes_dir,
            db_path=db_path
        )
        provider = MockProvider()
        store = MemoryStore(db_path)
        perm_engine = PermissionEngine()
        tool_registry = ToolRegistry(perm_engine, store)
        tool_registry.register(FilesystemTool(workspace))
        tool_registry.register(TerminalTool(workspace))

        agent = JarvisAgent(
            config=config,
            provider=provider,
            tool_registry=tool_registry,
            memory_store=store
        )
        yield agent, store


def test_intent_classification():
    assert IntentClassifier.classify("Remember that I prefer Gemini") == "REMEMBER_FACT"
    assert IntentClassifier.classify("What am I looking at?") == "SCREEN_QUERY"
    assert IntentClassifier.classify("Create a React application called Nova") == "ENGINEERING_ACTION"
    assert IntentClassifier.classify("Hello JARVIS, how are you?") == "GENERAL_CONVERSATION"


@pytest.mark.asyncio
async def test_agent_remember_fact(agent_environment):
    agent, store = agent_environment
    res = await agent.run("Remember that my main project is ResumeIQ AI")

    assert res["state"] == "SUCCESS"
    assert res["verified"] is True
    assert "ResumeIQ" in res["response"]

    # Verify directly in SQLite store
    memories = store.get_memories()
    assert len(memories) >= 1
    assert any("ResumeIQ AI" in m.content for m in memories)


@pytest.mark.asyncio
async def test_agent_interruption(agent_environment):
    agent, _ = agent_environment
    res = await agent.run("Stop")
    assert res["state"] == "IDLE"
    assert "halted" in res["response"].lower() or "interrupted" in res["response"].lower()


@pytest.mark.asyncio
async def test_agent_multi_step_execution_with_receipts(agent_environment):
    agent, _ = agent_environment
    res = await agent.run("Create a React application called Nova")

    assert res["state"] == "COMPLETED"
    assert res["verified"] is True
    assert "receipts" in res
    assert len(res["receipts"]) >= 3
    assert any("VERIFIED" in r for r in res["receipts"])
