#!/usr/bin/env python3
"""
JARVIS Preflight Verification System
Comprehensive end-to-end system verification for the actual running JARVIS system.
Tests configuration, security boundaries, permissions, tools, memory, providers, and agent loops.
Finishes with: N PASS | N FAIL | N WARN.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

