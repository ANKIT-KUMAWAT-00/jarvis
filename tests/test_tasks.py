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


def test_task_creation_and_listing(temp_scheduler):
    task = temp_scheduler.create_task(
        title="Compile TypeScript",
        description="Run npm build for frontend project",
        scheduled_delay_seconds=120.0
    )
    assert task.task_id.startswith("#J-")
    assert task.status == "QUEUED"
    assert task.scheduled_time is not None

    tasks = temp_scheduler.list_tasks(status="QUEUED")
    assert len(tasks) == 1
    assert tasks[0].task_id == task.task_id


def test_task_status_lifecycle(temp_scheduler):
    task = temp_scheduler.create_task(title="Inspect Backend")
    assert task.status == "QUEUED"

    # Transition to RUNNING
    ok = temp_scheduler.update_task_status(task.task_id, "RUNNING")
    assert ok is True

    running_tasks = temp_scheduler.list_tasks(status="RUNNING")
    assert len(running_tasks) == 1

    # Transition to COMPLETED
    temp_scheduler.update_task_status(task.task_id, "COMPLETED")
    completed = temp_scheduler.list_tasks(status="COMPLETED")
    assert len(completed) == 1
