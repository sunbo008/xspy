"""Unit tests for intermediate data persistence."""

from __future__ import annotations

from pathlib import Path

from xspy.core.models import NovelMetadata
from xspy.pipeline.persistence import IntermediatePersistence


class TestIntermediatePersistence:
    def test_save_and_load(self, tmp_path: Path):
        p = IntermediatePersistence(tmp_path)
        data = {"key": "value", "num": 42}
        p.save("test-novel", "stage1.json", data, module="test")

        loaded = p.load("test-novel", "stage1.json")
        assert loaded is not None
        assert loaded["data"]["key"] == "value"
        assert loaded["_meta"]["module"] == "test"

    def test_load_nonexistent(self, tmp_path: Path):
        p = IntermediatePersistence(tmp_path)
        assert p.load("nope", "nope.json") is None

    def test_exists(self, tmp_path: Path):
        p = IntermediatePersistence(tmp_path)
        assert not p.exists("novel", "data.json")
        p.save("novel", "data.json", {"x": 1}, module="test")
        assert p.exists("novel", "data.json")

    def test_save_pydantic_model(self, tmp_path: Path):
        p = IntermediatePersistence(tmp_path)
        meta = NovelMetadata(title="测试", author="作者", total_word_count=100)
        p.save("novel", "meta.json", meta, module="parser")

        loaded = p.load("novel", "meta.json")
        assert loaded is not None
        assert loaded["data"]["title"] == "测试"
