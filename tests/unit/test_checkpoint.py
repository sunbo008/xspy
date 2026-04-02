"""Unit tests for pipeline checkpoint."""

from __future__ import annotations

from pathlib import Path

from xspy.pipeline.checkpoint import Checkpoint


class TestCheckpoint:
    def test_save_and_load(self, tmp_path: Path):
        cp = Checkpoint(tmp_path)
        cp.save(
            "test-novel",
            completed_stages=["parse", "character"],
            completed_chapters={"screenwriter": [0, 1]},
            trace_id="t123",
        )
        data = cp.load("test-novel")
        assert data is not None
        assert data["completed_stages"] == ["parse", "character"]
        assert data["completed_chapters"]["screenwriter"] == [0, 1]

    def test_load_nonexistent(self, tmp_path: Path):
        cp = Checkpoint(tmp_path)
        assert cp.load("nonexistent") is None

    def test_is_stage_complete(self, tmp_path: Path):
        cp = Checkpoint(tmp_path)
        cp.save("novel", completed_stages=["parse"], completed_chapters={})
        assert cp.is_stage_complete("novel", "parse")
        assert not cp.is_stage_complete("novel", "screenwriter")

    def test_is_chapter_complete(self, tmp_path: Path):
        cp = Checkpoint(tmp_path)
        cp.save(
            "novel",
            completed_stages=[],
            completed_chapters={"screenwriter": [0, 1, 2]},
        )
        assert cp.is_chapter_complete("novel", "screenwriter", 1)
        assert not cp.is_chapter_complete("novel", "screenwriter", 5)

    def test_clear(self, tmp_path: Path):
        cp = Checkpoint(tmp_path)
        cp.save("novel", completed_stages=["x"], completed_chapters={})
        cp.clear("novel")
        assert cp.load("novel") is None
