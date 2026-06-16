"""
JARVIS System Configuration Module
Handles environment variables, default paths, and system settings.
"""

import os
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field

# Base Directory paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
DEFAULT_NOTES_DIR = DATA_DIR / "notes"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
