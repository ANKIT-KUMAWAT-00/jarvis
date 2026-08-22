"""
JARVIS Computer Vision / Screenshot Understanding Controller
Fallback mechanism when Accessibility tree or DOM selectors are insufficient
(e.g., canvas-rendered UIs, custom game engines, Electron apps with disabled AX).
"""

import asyncio
import os
