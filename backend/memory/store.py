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


