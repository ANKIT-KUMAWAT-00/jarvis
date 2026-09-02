"""
Tests for JARVIS macOS Automation:
Application Control, Meeting Scheduling, Timers, and Communication.
"""

import pytest
from pathlib import Path
from backend.tools.app_control import AppControlTool
from backend.tools.meeting_scheduler import MeetingSchedulerTool
from backend.tools.communication import CommunicationTool
from backend.agent.planner import IntentClassifier
from backend.agent.core import JarvisAgent
from backend.tools.registry import ToolRegistry
from backend.security.permissions import PermissionEngine
from backend.memory.store import MemoryStore
