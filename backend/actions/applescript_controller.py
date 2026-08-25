"""
JARVIS AppleScript Controller
Controls applications that expose AppleScript dictionaries:
Safari, Google Chrome, Terminal, Finder, Music, Spotify, and System Events.
"""

import asyncio
import os
import logging
from typing import Dict, Any, Optional
