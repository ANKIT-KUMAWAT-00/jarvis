"""
End-to-End (E2E) workflow test for JARVIS.
Simulates: User Request -> Intent -> Plan -> Safe Execution -> Verification -> Receipts -> Response.
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


@pytest.mark.asyncio
async def test_e2e_full_project_creation_workflow():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        db_path = workspace / "jarvis_e2e.db"
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

        # Execute complex request
        result = await agent.run("Create a React application called Nova")

        # 1. State must be COMPLETED
        assert result["state"] == "COMPLETED"

        # 2. Must be strictly verified
        assert result["verified"] is True

        # 3. Must have receipts proving actions
        assert len(result["receipts"]) >= 3
        for receipt in result["receipts"]:
            assert "VERIFIED" in receipt

        # 4. Physical artifacts must exist on disk and be verified
        target_file = workspace / "nova_app.json"
        assert target_file.exists()
        assert target_file.stat().st_size > 0

        # 5. Output response must explain what happened with evidence
        assert "Nova" in result["response"] or "Operation completed" in result["response"]
