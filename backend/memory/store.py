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
