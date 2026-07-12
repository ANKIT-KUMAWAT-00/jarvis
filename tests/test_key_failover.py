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


def test_gemini_provider_rotation():
    p = GeminiProvider(
        api_keys=["keyA", "keyB"],
        model_name="gemini-3.8-flash"
    )
    assert p.current_key_index == 0
    assert p.api_key == "keyA"

    # Rotate 1
    rotated = p.rotate_key("Rate limit on keyA")
    assert rotated is True
    assert p.current_key_index == 1
    assert p.api_key == "keyB"
    assert "Active: #2" in p.get_model_name()

    # Rotate wrap around
    rotated = p.rotate_key("Rate limit on keyB")
    assert rotated is True
    assert p.current_key_index == 0
    assert p.api_key == "keyA"


def test_gemini_upstream_error_detection():
    assert GeminiProvider._is_upstream_temporary_error("429 RESOURCE_EXHAUSTED: quota exceeded")
    assert GeminiProvider._is_upstream_temporary_error("503 UNAVAILABLE: high demand")
    assert GeminiProvider._is_upstream_temporary_error("500 INTERNAL server error")
    assert not GeminiProvider._is_upstream_temporary_error("Invalid argument: missing prompt")
