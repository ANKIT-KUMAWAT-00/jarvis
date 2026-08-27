"""
JARVIS Context Manager
Maintains conversational state, active task context, window/application awareness,
entity tracking, and multi-turn reference resolution.
"""

import time
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


