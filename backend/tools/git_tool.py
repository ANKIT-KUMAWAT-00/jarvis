"""
JARVIS Git Version Control Tool
Inspects repository state, diffs, branches, and commits with verified change receipts.
Enforces Level 2/3 confirmations for remote pushes and hard resets.
"""

import asyncio
import time
from pathlib import Path
