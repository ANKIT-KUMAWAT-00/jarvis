"""
JARVIS macOS Accessibility Controller
Interacts with applications via macOS Accessibility APIs (System Events UI Scripting).
Inspects accessibility trees, locates semantic buttons/inputs, clicks and types
without relying on brittle screen coordinates.
"""

import asyncio
import os
import json
import logging
from typing import Dict, Any, List, Optional
