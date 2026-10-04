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


def test_memory_relevance_search(temp_store):
    temp_store.add_memory(MemoryItem(content="Main project is ResumeIQ AI", category="project"))
    temp_store.add_memory(MemoryItem(content="User prefers dark theme", category="preference"))
    temp_store.add_memory(MemoryItem(content="Favorite beverage is coffee", category="long_term"))

    retriever = MemoryRetriever(temp_store)
    results = retriever.search_relevant("What is my main project?", limit=2)
    assert len(results) > 0
    assert any("ResumeIQ" in mem.content for mem, score in results)


def test_epistemic_separation(temp_store):
    temp_store.add_memory(MemoryItem(content="Prefer Gemini 2.5 Flash", category="preference"))
    retriever = MemoryRetriever(temp_store)
    context = retriever.build_epistemic_context("Which model do I prefer?")

    assert "KNOWN" in context
    assert "OBSERVED" in context
    assert "REMEMBERED" in context
    assert "INFERRED" in context
    assert "UNKNOWN" in context
    assert any("Gemini" in item for item in context["REMEMBERED"])
