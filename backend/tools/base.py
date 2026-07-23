"""
JARVIS Tool Abstraction Base
Defines the Tool interface, ToolResult, VerificationResult, and parameter schemas.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field
