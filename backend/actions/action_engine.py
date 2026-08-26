"""
JARVIS Unified Action Engine
Orchestrates high-level action abstractions across native macOS, AppleScript,
Accessibility APIs, Browser Automation, and Computer Vision fallback.
"""

import asyncio
import os
import time
import urllib.parse
from typing import Dict, Any, Optional
from .base import ActionCommand, ActionResult, ActionType
from .macos_controller import MacOSController
from .applescript_controller import AppleScriptController
