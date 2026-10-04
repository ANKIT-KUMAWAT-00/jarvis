"""
Unit tests for JARVIS Tools and Verification Engines.
"""

import pytest
import tempfile
from pathlib import Path
from backend.tools.filesystem import FilesystemTool
from backend.tools.terminal import TerminalTool
from backend.tools.system_info import SystemInfoTool
from backend.tools.browser_tool import BrowserTool
from backend.tools.screen_tool import ScreenVisionTool


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.mark.asyncio
async def test_filesystem_tool_lifecycle(temp_workspace):
    tool = FilesystemTool(temp_workspace)

    # 1. Write file
    w_res = await tool.execute({"action": "write_file", "path": "hello.txt", "content": "Hello JARVIS"})
    assert w_res.success is True

    # Verify write
    v_write = tool.verify(w_res, {"action": "write_file", "path": "hello.txt"})
    assert v_write.verified is True

    # 2. Read file
    r_res = await tool.execute({"action": "read_file", "path": "hello.txt"})
    assert r_res.success is True
    assert r_res.output == "Hello JARVIS"

    # 3. List dir
    l_res = await tool.execute({"action": "list_dir", "path": "."})
    assert l_res.success is True
    assert any(item["name"] == "hello.txt" for item in l_res.output)

    # 4. Traversal block
    t_res = await tool.execute({"action": "read_file", "path": "../../../etc/hosts"})
    assert t_res.success is False
    assert "Security Boundary" in t_res.error


@pytest.mark.asyncio
async def test_terminal_tool_execution(temp_workspace):
    tool = TerminalTool(temp_workspace)

    res = await tool.execute({"command": "echo 'TEST_OK'", "timeout": 5.0})
    assert res.success is True
    assert "TEST_OK" in res.output

    v_res = tool.verify(res, {"expected_exit_code": 0, "output_contains": "TEST_OK"})
    assert v_res.verified is True


@pytest.mark.asyncio
async def test_terminal_tool_blocks_destructive_command(temp_workspace):
    tool = TerminalTool(temp_workspace)
    res = await tool.execute({"command": "rm -rf /"})
    assert res.success is False
    assert "Security Intercept" in res.error


@pytest.mark.asyncio
async def test_system_info_tool():
    tool = SystemInfoTool()
    res = await tool.execute({})
    assert res.success is True
    assert "os" in res.output
    assert "tools" in res.output
    assert res.raw_data.get("architecture") in ("arm64", "x86_64")


@pytest.mark.asyncio
async def test_browser_tool_wrapping():
    tool = BrowserTool()
    # Test safe handling when given an invalid or local test URL
    res = await tool.execute({"url": "http://127.0.0.1:9999/nonexistent"})
    # Either connection error or response, error handling must be clean and not crash
    assert isinstance(res.success, bool)
