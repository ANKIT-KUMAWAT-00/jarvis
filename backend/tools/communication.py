"""
JARVIS Communication Tool
Enables composing and sending emails via macOS Mail, messages via macOS Messages,
and placing audio/video calls via FaceTime or available communication apps.
"""

import asyncio
import os
import urllib.parse
from typing import Dict, Any, Optional
from .base import Tool, ToolResult, VerificationResult
