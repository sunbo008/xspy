"""Intermediate data persistence — save/load module outputs to JSON."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from xspy.core.models import IntermediateMetaHeader

logger = structlog.get_logger()


class IntermediatePersistence:
    """Handles reading and writing intermediate JSON data files."""

    def __init__(self, base_dir: str | Path) -> None:
        self._base_dir = Path(base_dir)

    def _ensure_dir(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        novel_slug: str,
        filename: str,
        data: Any,
        *,
        module: str,
        trace_id: str = "",
    ) -> Path:
        """Save intermediate data with metadata header."""
        meta = IntermediateMetaHeader(
            module=module,
            timestamp=datetime.now(),
            trace_id=trace_id,
        )

        full_data = {
            "_meta": meta.model_dump(mode="json"),
            "data": data
            if isinstance(data, (dict, list))
            else json.loads(
                data.model_dump_json() if hasattr(data, "model_dump_json") else json.dumps(data)
            ),
        }

        path = self._base_dir / novel_slug / filename
        self._ensure_dir(path)
        path.write_text(
            json.dumps(full_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("persistence.saved", path=str(path), module=module)
        return path

    def load(self, novel_slug: str, filename: str) -> dict[str, Any] | None:
        """Load intermediate data. Returns None if file doesn't exist."""
        path = self._base_dir / novel_slug / filename
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, novel_slug: str, filename: str) -> bool:
        return (self._base_dir / novel_slug / filename).exists()
