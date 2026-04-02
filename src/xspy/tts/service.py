"""TTSClientService: sends synthesis requests to TTS servers."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx
import structlog

from xspy.core.exceptions import TTSConnectionError, TTSTimeoutError
from xspy.core.models import TTSMetadata, TTSRequest, TTSResponse

logger = structlog.get_logger()


class TTSClientService:
    """HTTP client for TTS inference servers (Index-TTS, Qwen3-TTS, etc)."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: int = 60,
        max_retries: int = 3,
        output_dir: str | Path = "data/tts_output",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._client = httpx.Client(timeout=timeout)

    def process(self, input: TTSRequest) -> TTSResponse:
        log = logger.bind(voice_id=input.voice_id, text_length=len(input.text))
        log.info("tts.request")

        start = time.monotonic()
        audio_path = self._synthesize(input, log)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        log.info("tts.done", elapsed_ms=elapsed_ms, output=str(audio_path))

        return TTSResponse(
            audio_path=audio_path,
            engine_used=input.tts_engine,
            metadata=TTSMetadata(latency_ms=elapsed_ms),
        )

    def _synthesize(self, req: TTSRequest, log: structlog.BoundLogger) -> Path:
        """Send request to TTS server and save the returned audio."""
        payload: dict[str, Any] = {
            "text": req.text,
            "voice_id": req.voice_id,
        }

        if req.reference_audio_path:
            payload["reference_audio"] = req.reference_audio_path
        if req.emotion_params:
            payload["speed"] = req.emotion_params.speed
            payload["pitch_shift"] = req.emotion_params.pitch_shift
            payload["energy"] = req.emotion_params.energy
        payload.update(req.engine_params)

        endpoint = f"{self._base_url}/synthesize"

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._client.post(endpoint, json=payload)
                response.raise_for_status()
                break
            except httpx.TimeoutException as e:
                log.warning("tts.timeout", attempt=attempt)
                if attempt == self._max_retries:
                    raise TTSTimeoutError(
                        f"TTS timed out after {self._max_retries} attempts",
                        module="tts",
                    ) from e
            except httpx.HTTPError as e:
                log.warning("tts.http_error", attempt=attempt, error=str(e))
                if attempt == self._max_retries:
                    raise TTSConnectionError(
                        f"TTS server error: {e}",
                        module="tts",
                        context={"endpoint": endpoint},
                    ) from e

        output_path = self._output_dir / f"{req.voice_id}_{hash(req.text) & 0xFFFFFFFF:08x}.wav"
        output_path.write_bytes(response.content)
        return output_path

    def close(self) -> None:
        self._client.close()
