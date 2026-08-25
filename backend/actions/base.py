"""
JARVIS Action Abstraction Layer - Base Types
High-level action interfaces decouples intent from underlying OS controllers.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


