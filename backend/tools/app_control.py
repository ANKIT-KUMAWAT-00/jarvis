"""
JARVIS macOS Application Control Tool
Enables launching, managing, checking installation, navigating the Mac App Store,
opening macOS System Settings privacy panes, and controlling web URLs without hardcoding.
"""

import asyncio
import subprocess
import json
import os
import shutil
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
