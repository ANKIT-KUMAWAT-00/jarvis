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


def test_add_and_retrieve_memory(temp_store):
    item = MemoryItem(
        category="preference",
        content="User prefers Python and strict verification",
        source="user",
        confidence="explicit"
    )
    mem_id = temp_store.add_memory(item)
    assert mem_id > 0

    memories = temp_store.get_memories(category="preference")
    assert len(memories) == 1
    assert memories[0].content == "User prefers Python and strict verification"
    assert memories[0].confidence == "explicit"


def test_memory_count_and_delete(temp_store):
    assert temp_store.count_memories() == 0
    id1 = temp_store.add_memory(MemoryItem(content="Fact 1", category="long_term"))
    id2 = temp_store.add_memory(MemoryItem(content="Fact 2", category="project"))
    assert temp_store.count_memories() == 2

    temp_store.delete_memory(id1)
    assert temp_store.count_memories() == 1
    remaining = temp_store.get_memories()
    assert remaining[0].id == id2


