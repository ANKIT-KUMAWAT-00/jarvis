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
