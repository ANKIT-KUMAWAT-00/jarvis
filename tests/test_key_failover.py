import pytest
from backend.providers.gemini import GeminiProvider


def test_gemini_provider_key_pool_collection():
    p = GeminiProvider(
        api_key="key1",
        backup_keys=["key2", "key3"],
        model_name="gemini-3.8-flash"
    )
    assert p.api_keys == ["key1", "key2", "key3"]
    assert p.current_key_index == 0
    assert p.get_model_name() == "gemini-3.8-flash (Pool: 3 keys, Active: #1)"


