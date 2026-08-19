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
