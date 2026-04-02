"""Unit tests for LLM layer: cache, router, validator."""

from __future__ import annotations

from pathlib import Path

import pytest

from xspy.core.exceptions import LLMCacheMissError, LLMResponseError
from xspy.core.llm.cache import LLMCache
from xspy.core.llm.client import ModelConfig
from xspy.core.llm.router import ModelRouter
from xspy.core.llm.validator import validate_json_output


class TestLLMCache:
    def test_put_and_get(self, tmp_path: Path):
        cache = LLMCache(tmp_path / "cache")
        messages = [{"role": "user", "content": "hello"}]

        cache.put("model-a", messages, "world")
        result = cache.get("model-a", messages)
        assert result == "world"

    def test_miss(self, tmp_path: Path):
        cache = LLMCache(tmp_path / "cache")
        result = cache.get("model-a", [{"role": "user", "content": "new"}])
        assert result is None

    def test_get_or_raise(self, tmp_path: Path):
        cache = LLMCache(tmp_path / "cache")
        with pytest.raises(LLMCacheMissError):
            cache.get_or_raise("model-a", [{"role": "user", "content": "new"}])

    def test_disabled(self, tmp_path: Path):
        cache = LLMCache(tmp_path / "cache", enabled=False)
        cache.put("model-a", [{"role": "user", "content": "hello"}], "world")
        assert cache.get("model-a", [{"role": "user", "content": "hello"}]) is None

    def test_different_models_different_keys(self, tmp_path: Path):
        cache = LLMCache(tmp_path / "cache")
        messages = [{"role": "user", "content": "same"}]
        cache.put("model-a", messages, "response-a")
        cache.put("model-b", messages, "response-b")
        assert cache.get("model-a", messages) == "response-a"
        assert cache.get("model-b", messages) == "response-b"

    def test_clear(self, tmp_path: Path):
        cache = LLMCache(tmp_path / "cache")
        cache.put("m", [{"role": "user", "content": "x"}], "y")
        count = cache.clear()
        assert count == 1
        assert cache.get("m", [{"role": "user", "content": "x"}]) is None


class TestModelRouter:
    @staticmethod
    def _make_configs() -> list[ModelConfig]:
        return [
            ModelConfig(
                id="model-a",
                name="A",
                base_url="http://localhost:8000/v1",
                capabilities=["screenwriter", "character-analysis"],
                priority=1,
            ),
            ModelConfig(
                id="model-b",
                name="B",
                base_url="http://localhost:8001/v1",
                capabilities=["screenwriter"],
                priority=2,
            ),
        ]

    def test_route_by_task(self):
        configs = self._make_configs()
        router = ModelRouter(configs, {"screenwriter": "model-a"})
        assert router.get_model_for_task("screenwriter") == "model-a"

    def test_fallback_by_capability(self):
        configs = self._make_configs()
        router = ModelRouter(configs, {"screenwriter": "nonexistent"})
        result = router.get_model_for_task("screenwriter")
        assert result == "model-a"  # highest priority with capability

    def test_fallback_by_priority(self):
        configs = self._make_configs()
        router = ModelRouter(configs, {})
        result = router.get_model_for_task("emotion-inference")
        assert result == "model-a"  # no explicit routing, falls back to priority


class TestValidateJsonOutput:
    def test_valid_json(self):
        result = validate_json_output('{"key": "value"}')
        assert result == {"key": "value"}

    def test_code_fence_stripping(self):
        raw = '```json\n{"key": "value"}\n```'
        result = validate_json_output(raw)
        assert result == {"key": "value"}

    def test_invalid_json(self):
        with pytest.raises(LLMResponseError, match="not valid JSON"):
            validate_json_output("not json at all")

    def test_required_fields(self):
        with pytest.raises(LLMResponseError, match="Missing required fields"):
            validate_json_output('{"a": 1}', required_fields=["b", "c"])

    def test_required_fields_satisfied(self):
        result = validate_json_output('{"a": 1, "b": 2}', required_fields=["a", "b"])
        assert result == {"a": 1, "b": 2}

    def test_expected_type_dict(self):
        with pytest.raises(LLMResponseError, match="Expected dict"):
            validate_json_output("[1, 2, 3]", expected_type=dict)

    def test_expected_type_list(self):
        result = validate_json_output("[1, 2, 3]", expected_type=list)
        assert result == [1, 2, 3]
