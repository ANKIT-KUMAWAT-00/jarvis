"""
JARVIS Extensible Skill Architecture
Defines base interfaces, manifest schemas, and registry for modular capabilities.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path


