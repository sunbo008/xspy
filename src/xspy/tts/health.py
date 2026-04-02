"""TTS server health checker — periodic availability monitoring."""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class HealthStatus:
    """Health status of a TTS server."""

    url: str
    engine: str
    is_healthy: bool = False
    last_check_ms: int = 0
    latency_ms: int = 0
    error: str = ""


class TTSHealthChecker:
    """Monitors TTS server availability."""

    def __init__(self, timeout: int = 5) -> None:
        self._timeout = timeout
        self._history: dict[str, list[HealthStatus]] = {}

    def check(self, base_url: str, *, engine: str = "unknown") -> HealthStatus:
        """Ping a TTS server and return its health status."""
        url = f"{base_url.rstrip('/')}/health"
        start = time.monotonic()

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(url)
                latency_ms = int((time.monotonic() - start) * 1000)

                status = HealthStatus(
                    url=base_url,
                    engine=engine,
                    is_healthy=resp.status_code == 200,
                    latency_ms=latency_ms,
                )
        except Exception as e:
            status = HealthStatus(
                url=base_url,
                engine=engine,
                is_healthy=False,
                error=str(e),
            )

        status.last_check_ms = int(time.time() * 1000)
        self._history.setdefault(base_url, []).append(status)

        level = "info" if status.is_healthy else "warning"
        getattr(logger, level)(
            "tts.health",
            url=base_url,
            engine=engine,
            healthy=status.is_healthy,
            latency_ms=status.latency_ms,
        )
        return status

    def check_all(self, servers: list[dict[str, str]]) -> list[HealthStatus]:
        """Check multiple servers. Each dict has 'url' and 'engine' keys."""
        return [self.check(s["url"], engine=s.get("engine", "unknown")) for s in servers]

    def get_history(self, base_url: str) -> list[HealthStatus]:
        return self._history.get(base_url, [])
