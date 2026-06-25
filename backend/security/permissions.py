"""
JARVIS Security & Permission Engine
Implements strict Action Levels (LEVEL 0 to LEVEL 3) and narrow confirmation tokens.
"""

from enum import IntEnum
import time
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ActionLevel(IntEnum):
    LEVEL_0_READ = 0        # Read-only operations, zero confirmation needed
    LEVEL_1_SAFE_WRITE = 1  # Safe workspace writes, auto-performed on user intent
    LEVEL_2_EXTERNAL = 2    # External actions (push, external calls), confirmation required
    LEVEL_3_HIGH_RISK = 3   # Destructive commands, data deletion, force push: ALWAYS confirmed


