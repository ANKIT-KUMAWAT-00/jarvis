"""
JARVIS Terminal Tool
Controlled asynchronous shell execution with strict timeout, output capture,
secret masking, and exit status verification.
"""

import asyncio
import os
import time
from pathlib import Path
