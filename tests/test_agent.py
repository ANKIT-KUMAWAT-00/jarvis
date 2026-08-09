"""
Integration tests for JARVIS Agent core loop, intent routing, and execution.
"""

import pytest
import tempfile
from pathlib import Path
from backend.config import JarvisConfig
from backend.providers.mock import MockProvider
from backend.tools.registry import ToolRegistry
from backend.tools.filesystem import FilesystemTool
from backend.tools.terminal import TerminalTool
from backend.memory.store import MemoryStore
from backend.security.permissions import PermissionEngine
from backend.agent.core import JarvisAgent
