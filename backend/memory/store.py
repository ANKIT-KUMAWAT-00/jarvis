"""
JARVIS Persistent Memory Store (SQLite)
Manages short-term, long-term, project, preference, and task memories.
Ensures atomic transactions and instant persistence.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    id: Optional[int] = None
    category: str = Field(default="long_term", description="short_term, long_term, project, preference, task")
    content: str
    source: str = Field(default="user", description="user, agent, observation")
    confidence: str = Field(default="explicit", description="explicit, observed, inferred")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActivityRecord(BaseModel):
    id: Optional[int] = None
    task_id: str
    tool_name: str
    action: str
    status: str
    duration_ms: int = 0
    error_category: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database tables with optimal indexing."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Memories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    metadata_json TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories(category)")
            
            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    scheduled_time TEXT,
                    recovery_policy TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")

            # Activity log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    tool_name TEXT,
                    action TEXT,
                    status TEXT,
                    duration_ms INTEGER,
                    error_category TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_log(timestamp)")
            conn.commit()

    def add_memory(self, item: MemoryItem) -> int:
        """Persist a new memory entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memories (category, content, source, confidence, created_at, updated_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                item.category,
                item.content,
                item.source,
                item.confidence,
                item.created_at,
                datetime.utcnow().isoformat(),
                json.dumps(item.metadata)
            ))
            conn.commit()
            return cursor.lastrowid

    def get_memories(self, category: Optional[str] = None, limit: int = 50) -> List[MemoryItem]:
        """Fetch memories, optionally filtered by category."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    "SELECT * FROM memories WHERE category = ? ORDER BY id DESC LIMIT ?",
                    (category, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM memories ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
            rows = cursor.fetchall()
            items = []
            for r in rows:
                meta = {}
                if r["metadata_json"]:
                    try:
                        meta = json.loads(r["metadata_json"])
                    except Exception:
                        pass
                items.append(MemoryItem(
                    id=r["id"],
                    category=r["category"],
                    content=r["content"],
                    source=r["source"],
                    confidence=r["confidence"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    metadata=meta
                ))
            return items

    def delete_memory(self, memory_id: int) -> bool:
        """Remove a memory by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    def log_activity(self, record: ActivityRecord):
        """Record an activity in the audit log."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO activity_log (task_id, tool_name, action, status, duration_ms, error_category, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record.task_id,
                record.tool_name,
                record.action,
                record.status,
                record.duration_ms,
                record.error_category,
                record.timestamp
            ))
            conn.commit()

    def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recent system activity."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) for r in cursor.fetchall()]

    def count_memories(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memories")
            return cursor.fetchone()[0]
