"""
JARVIS Intent & Goal Parser
Extracts goals, target applications, entities, and actions from natural language,
resolving pronouns and conversational references.
"""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


