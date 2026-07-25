"""
JARVIS Screen Vision Tool
Captures macOS screen frames dynamically using native screencapture utility,
encodes to base64 for Gemini Vision multimodal analysis.
Never relies on stale cached frames.
"""

import asyncio
import base64
import time
