"""
JARVIS macOS Controller
Native macOS API operations: launches applications, manages window focus,
opens files and projects, navigates System Settings, and controls app lifecycles.
"""

import asyncio
import os
import urllib.parse
from pathlib import Path
