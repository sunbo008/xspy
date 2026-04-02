"""Checkpoint persistence for pipeline resume."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import structlog

logger = structlog.get_logger()


class Checkpoint:
    """Manages pipeline checkpoint state for resume-from-failure."""

    def __init__(self, checkpoint_dir: str | Path) -> None:
        self._dir = Path(checkpoint_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, novel_slug: str) -> Path:
        return self._dir / f"{novel_slug}.json"

    def save(
        self,
        novel_slug: str,
        *,
        completed_stages: list[str],
        completed_chapters: dict[str, list[int]],
        trace_id: str = "",
    ) -> None:
        """Save checkpoint state."""
        data = {
            "novel_slug": novel_slug,
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "completed_stages": completed_stages,
            "completed_chapters": completed_chapters,
        }
        self._path(novel_slug).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("checkpoint.saved", novel_slug=novel_slug, stages=completed_stages)

    def load(self, novel_slug: str) -> dict | None:
        """Load checkpoint. Returns None if no checkpoint exists."""
        path = self._path(novel_slug)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def is_stage_complete(self, novel_slug: str, stage: str) -> bool:
        """Check if a pipeline stage is already complete."""
        cp = self.load(novel_slug)
        if not cp:
            return False
        return stage in cp.get("completed_stages", [])

    def is_chapter_complete(self, novel_slug: str, stage: str, chapter_index: int) -> bool:
        """Check if a specific chapter is complete for a given stage."""
        cp = self.load(novel_slug)
        if not cp:
            return False
        chapters = cp.get("completed_chapters", {}).get(stage, [])
        return chapter_index in chapters

    def clear(self, novel_slug: str) -> None:
        """Remove checkpoint."""
        path = self._path(novel_slug)
        if path.exists():
            path.unlink()
            logger.info("checkpoint.cleared", novel_slug=novel_slug)
