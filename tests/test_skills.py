"""
Unit tests for JARVIS Modular Skill Architecture.
"""

import pytest
import tempfile
from pathlib import Path
from skills.base import SkillRegistry
from skills.coding.skill import CodingSkill
from skills.filesystem.skill import FilesystemSkill
from skills.browser.skill import BrowserSkill
from skills.vision.skill import VisionSkill
from skills.reminders.skill import RemindersSkill
from skills.custom.skill import CustomSkill
from backend.memory.store import MemoryStore
from backend.tasks.scheduler import TaskScheduler


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.mark.asyncio
async def test_skill_registry_and_manifests(temp_dir):
    store = MemoryStore(temp_dir / "test.db")
    scheduler = TaskScheduler(store)

    registry = SkillRegistry()
    coding = CodingSkill(temp_dir)
    fs = FilesystemSkill(temp_dir)
    browser = BrowserSkill()
    vision = VisionSkill(temp_dir / "scratch")
    reminders = RemindersSkill(scheduler)
    custom = CustomSkill()

    registry.register(coding)
    registry.register(fs)
    registry.register(browser)
    registry.register(vision)
    registry.register(reminders)
    registry.register(custom)

    skills = registry.list_skills()
    assert len(skills) == 6
    names = [s["name"] for s in skills]
    assert "coding" in names
    assert "filesystem" in names
    assert "browser" in names
    assert "vision" in names
    assert "reminders" in names
    assert "custom_extension" in names


@pytest.mark.asyncio
async def test_filesystem_skill_execution(temp_dir):
    fs = FilesystemSkill(temp_dir)
    await fs.initialize()

    # Write file via capability
    res = await fs.execute_capability("write_file", {"path": "skill_test.txt", "content": "SKILL_OK"})
    assert res["success"] is True

    # Read file via capability
    res_read = await fs.execute_capability("read_file", {"path": "skill_test.txt"})
    assert res_read["success"] is True
    assert res_read["output"] == "SKILL_OK"


@pytest.mark.asyncio
async def test_custom_skill_execution():
    custom = CustomSkill()
    res = await custom.execute_capability("custom_action", {"param1": "value1"})
    assert res["success"] is True
    assert "param1" in res["message"]
