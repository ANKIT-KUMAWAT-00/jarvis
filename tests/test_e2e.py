"""
End-to-End (E2E) workflow test for JARVIS.
Simulates: User Request -> Intent -> Plan -> Safe Execution -> Verification -> Receipts -> Response.
"""

import pytest
import tempfile
from pathlib import Path
from backend.config import JarvisConfig
from backend.providers.mock import MockProvider
