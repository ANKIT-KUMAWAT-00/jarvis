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
