"""
Unit tests for JARVIS Memory Store, Search, and Epistemic Categorization.
"""

import pytest
import tempfile
from pathlib import Path
from backend.memory.store import MemoryStore, MemoryItem
from backend.memory.search import MemoryRetriever


@pytest.fixture
def temp_store():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        store = MemoryStore(Path(tmp.name))
        yield store


