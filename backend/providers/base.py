"""
JARVIS LLM Provider Abstraction
Decouples agent logic from specific model providers (Gemini, Mock, Future).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
