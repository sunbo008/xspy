"""LLM response cache — disk-based JSON, keyed by prompt hash + model_id."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import structlog

from xspy.core.exceptions import LLMCacheMissError

logger = structlog.get_logger()


class LLMCache:
    """Disk-based LLM response cache for deterministic replay."""

    def __init__(self, cache_dir: str | Path, *, enabled: bool = True) -> None:
        self._cache_dir = Path(cache_dir)
        self._enabled = enabled
        if enabled:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _make_key(model_id: str, messages: list[dict[str, str]]) -> str:
        """Create a cache key from model ID and messages."""
        content = json.dumps({"model_id": model_id, "messages": messages}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:24]

    def get(self, model_id: str, messages: list[dict[str, str]]) -> str | None:
        """Try to get a cached response."""
        if not self._enabled:
            return None

        key = self._make_key(model_id, messages)
        cache_file = self._cache_dir / f"{key}.json"

        if cache_file.exists():
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            logger.debug("llm.cache.hit", key=key, model_id=model_id)
            return data["response"]

        logger.debug("llm.cache.miss", key=key, model_id=model_id)
        return None

    def get_or_raise(self, model_id: str, messages: list[dict[str, str]]) -> str:
        """Get cached response or raise LLMCacheMissError (for replay-only mode)."""
        result = self.get(model_id, messages)
        if result is None:
            raise LLMCacheMissError(
                "Cache miss in replay-only mode",
                module="llm.cache",
                context={"model_id": model_id},
            )
        return result

    def put(self, model_id: str, messages: list[dict[str, str]], response: str) -> None:
        """Store a response in the cache."""
        if not self._enabled:
            return

        key = self._make_key(model_id, messages)
        cache_file = self._cache_dir / f"{key}.json"
        data = {
            "model_id": model_id,
            "messages": messages,
            "response": response,
        }
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.debug("llm.cache.stored", key=key, model_id=model_id)

    def clear(self) -> int:
        """Remove all cached entries. Returns count of removed files."""
        count = 0
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                f.unlink()
                count += 1
        return count
