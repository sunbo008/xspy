"""Index-TTS 1.5/2 HTTP client implementation."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx
import structlog

from xspy.core.exceptions import TTSConnectionError, TTSTimeoutError
from xspy.core.models import TTSMetadata, TTSRequest, TTSResponse

logger = structlog.get_logger()


class IndexTTSClient:
    """HTTP client specialized for Index-TTS inference server."""

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
        log = logger.bind(engine="index-tts", voice_id=input.voice_id)
        log.info("index_tts.synthesize", text_len=len(input.text))

        start = time.monotonic()

        payload: dict[str, Any] = {
            "text": input.text,
            "prompt_wav": input.reference_audio_path or "",
        }
        if input.emotion_params:
            payload["speed"] = input.emotion_params.speed

        audio_bytes = self._call_api("/api/tts", payload, log)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        output_path = self._output_dir / f"{input.voice_id}_{hash(input.text) & 0xFFFFFFFF:08x}.wav"
        output_path.write_bytes(audio_bytes)

        log.info("index_tts.done", elapsed_ms=elapsed_ms)
        return TTSResponse(
            audio_path=output_path,
            engine_used="index-tts",
            metadata=TTSMetadata(latency_ms=elapsed_ms, model_name="index-tts"),
        )

    def _call_api(self, endpoint: str, payload: dict, log: Any) -> bytes:
        url = f"{self._base_url}{endpoint}"
        for attempt in range(1, self._max_retries + 1):
            try:
                resp = self._client.post(url, json=payload)
                resp.raise_for_status()
                return resp.content
            except httpx.TimeoutException as e:
                log.warning("index_tts.timeout", attempt=attempt)
                if attempt == self._max_retries:
                    raise TTSTimeoutError(
                        f"Index-TTS timed out after {self._max_retries} attempts",
                        module="tts.index",
                    ) from e
            except httpx.HTTPError as e:
                log.warning("index_tts.error", attempt=attempt, error=str(e))
                if attempt == self._max_retries:
                    raise TTSConnectionError(
                        f"Index-TTS error: {e}",
                        module="tts.index",
                    ) from e
        raise TTSConnectionError("Unreachable", module="tts.index")

    def close(self) -> None:
        self._client.close()
