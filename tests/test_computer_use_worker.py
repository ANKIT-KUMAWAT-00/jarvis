"""
Comprehensive Tests for JARVIS Universal Computer-Use Worker Architecture.
Validates:
1. Universal Computer-Use Behavior:
   - 'Open WhatsApp and open Krishna's chat' (worker does not stop after opening WhatsApp)
   - 'Open Safari and search for something'
   - 'Open VS Code and run my project'
   - 'Open Spotify and play my playlist'
   - 'Open Gmail and send this email'
2. Context Manager & Multi-Turn Reference Resolution:
   - 'Open VS Code and open my ResumeIQ project' -> 'Run it'
   - 'Open Spotify' -> 'Play my workout playlist'
   - 'Open WhatsApp in Safari' -> 'Open Krishna's chat'
   - 'Open WhatsApp and message Krishna' -> 'Send her this message'
3. Ordinal Reference Resolution:
   - 'Play the second playlist' / 'Open the first one'
4. Task State Survival across Pauses & 'Continue' Resumption:
   - Preserves pending subtasks; resumes on 'continue'
5. Verification Integrity:
   - Opening an app is not task completion; never claims false success on partial completion
6. Capability Registry & Action Abstraction:
   - Non-hardcoded capability discovery and layer selection
"""

import pytest
import tempfile
from pathlib import Path
from backend.config import JarvisConfig
from backend.providers.mock import MockProvider
from backend.tools.registry import ToolRegistry
from backend.tools.app_control import AppControlTool
from backend.tools.communication import CommunicationTool
from backend.tools.terminal import TerminalTool
