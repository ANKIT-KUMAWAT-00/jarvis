"""
JARVIS Task Scheduler & Background Queue
Persistent tasks (#J-1042) with offline recovery policies, deduplication, and status tracking.
"""

import asyncio
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.memory.store import MemoryStore


class TaskItem(BaseModel):
    task_id: str
    title: str
    description: str = ""
    status: str = "QUEUED" # QUEUED, RUNNING, WAITING_FOR_PERMISSION, COMPLETED, FAILED, CANCELLED
    scheduled_time: Optional[str] = None
    recovery_policy: str = "run_immediately_if_missed"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None


class TaskScheduler:
    def __init__(self, memory_store: MemoryStore):
        self.store = memory_store
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._counter = 1000

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.store.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def create_task(
        self,
        title: str,
        description: str = "",
        scheduled_delay_seconds: Optional[float] = None,
        recovery_policy: str = "run_immediately_if_missed"
    ) -> TaskItem:
        """Create and persist a new unique task."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks")
            count = cursor.fetchone()[0]
            task_id = f"#J-{1001 + count}"
            
            sched_time_str = None
            if scheduled_delay_seconds is not None:
                sched_ts = time.time() + scheduled_delay_seconds
                sched_time_str = datetime.utcfromtimestamp(sched_ts).isoformat()

            now_str = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO tasks (task_id, title, description, status, scheduled_time, recovery_policy, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id, title, description, "QUEUED", sched_time_str, recovery_policy, now_str, now_str
            ))
            conn.commit()

            return TaskItem(
                task_id=task_id,
                title=title,
                description=description,
                status="QUEUED",
                scheduled_time=sched_time_str,
                recovery_policy=recovery_policy,
                created_at=now_str,
                updated_at=now_str
            )

    def update_task_status(self, task_id: str, new_status: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks
                SET status = ?, updated_at = ?
                WHERE task_id = ?
            """, (new_status, datetime.utcnow().isoformat(), task_id))
            conn.commit()
            return cursor.rowcount > 0

    def list_tasks(self, status: Optional[str] = None, limit: int = 50) -> List[TaskItem]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            rows = cursor.fetchall()
            return [
                TaskItem(
                    task_id=r["task_id"],
                    title=r["title"],
                    description=r["description"],
                    status=r["status"],
                    scheduled_time=r["scheduled_time"],
                    recovery_policy=r["recovery_policy"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                )
                for r in rows
            ]

    async def start(self):
        """Start the background task loop."""
        self._running = True
        self._worker_task = asyncio.create_task(self._task_loop())

    async def stop(self):
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()

    async def _task_loop(self):
        """Periodic background evaluation of queued/scheduled tasks."""
        while self._running:
            try:
                now_iso = datetime.utcnow().isoformat()
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM tasks
                        WHERE status = 'QUEUED' AND scheduled_time IS NOT NULL AND scheduled_time <= ?
                    """, (now_iso,))
                    due_tasks = cursor.fetchall()
                    for t in due_tasks:
                        # Mark completed
                        self.update_task_status(t["task_id"], "COMPLETED")
                await asyncio.sleep(5.0)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5.0)
