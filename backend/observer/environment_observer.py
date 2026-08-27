"""
JARVIS Environment Observer
Continuously observes macOS computer state: running applications, active windows,
browser tabs, accessibility elements, and system dialogs.
"""

import asyncio
import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

