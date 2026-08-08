"""
JARVIS Task State Manager
Maintains task execution state across permission prompts, App Store installations,
multi-turn interruptions, and seamless 'Continue' resumption.
"""

import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
