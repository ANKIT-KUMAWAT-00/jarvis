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


@pytest.mark.asyncio
async def test_agent_conversation_history_and_task_tracking(agent_environment):
    agent, store = agent_environment
    # 1. Run a task
    res1 = await agent.run("Create a React application called Nova")
    assert res1["state"] == "COMPLETED"
    assert len(agent.recent_task_records) == 1
    assert "Nova" in agent.recent_task_records[0]["goal"]

    # 2. General conversation turn
    res2 = await agent.run("What did you just build?")
    assert res2["state"] == "COMPLETED"
    # Verify agent conversation history recorded both user and assistant
    assert len(agent.conversation_history) >= 2
    assert any("What did you just build?" in msg["content"] for msg in agent.conversation_history)


@pytest.mark.asyncio
async def test_agent_learns_from_user_mistake_correction(agent_environment):
    agent, store = agent_environment
    # User corrects JARVIS
    correction_text = "No, that is not complete, you forgot to create the tailwind config"
    res = await agent.run(correction_text)

    # Verify a correction was saved to memory store
    corrections = store.get_memories(category="correction")
    assert len(corrections) >= 1
    assert any("tailwind" in c.content.lower() for c in corrections)

    # Verify epistemic context builder includes the learned correction
    epistemic_dict = agent.retriever.build_epistemic_context(
        query="How to configure styling?",
        recent_tasks=agent.recent_task_records
    )
    assert len(epistemic_dict["LEARNED_CORRECTIONS"]) >= 1
    assert any("tailwind" in c.lower() for c in epistemic_dict["LEARNED_CORRECTIONS"])

    context_str = agent.retriever.format_context_for_prompt(epistemic_dict)
    assert "LEARNED_CORRECTIONS" in context_str
    assert "tailwind" in context_str.lower()


