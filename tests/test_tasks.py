"""
Unit tests for JARVIS Task Scheduler and Persistent Background Queue.
"""

import pytest
import tempfile
from pathlib import Path
from backend.memory.store import MemoryStore
from backend.tasks.scheduler import TaskScheduler, TaskItem


@pytest.fixture
def temp_scheduler():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        store = MemoryStore(Path(tmp.name))
        scheduler = TaskScheduler(store)
        yield scheduler


