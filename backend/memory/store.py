"""
JARVIS Persistent Memory Store (SQLite)
Manages short-term, long-term, project, preference, and task memories.
Ensures atomic transactions and instant persistence.
"""

import sqlite3
import json
