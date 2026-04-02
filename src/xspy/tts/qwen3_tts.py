"""Qwen3-TTS via vLLM HTTP client implementation."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx
import structlog

from xspy.core.exceptions import TTSConnectionError, TTSTimeoutError
from xspy.core.models import TTSMetadata, TTSRequest, TTSResponse

logger = structlog.get_logger()


class Qwen3TTSClient:
    """HTTP client specialized for Qwen3-TTS served via vLLM."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: int = 120,
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
        log = logger.bind(engine="qwen3-tts", voice_id=input.voice_id)
        log.info("qwen3_tts.synthesize", text_len=len(input.text))

        start = time.monotonic()

        payload: dict[str, Any] = {
            "text": input.text,
            "voice_id": input.voice_id,
            "reference_audio": input.reference_audio_path or "",
        }
        if input.emotion_params:
            payload["speed"] = input.emotion_params.speed
            if input.emotion_params.style:
                payload["style"] = input.emotion_params.style

        audio_bytes = self._call_api("/v1/audio/speech", payload, log)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        output_path = (
            self._output_dir / f"qwen_{input.voice_id}_{hash(input.text) & 0xFFFFFFFF:08x}.wav"
        )
        output_path.write_bytes(audio_bytes)

        log.info("qwen3_tts.done", elapsed_ms=elapsed_ms)
        return TTSResponse(
            audio_path=output_path,
            engine_used="qwen3-tts",
            metadata=TTSMetadata(latency_ms=elapsed_ms, model_name="qwen3-tts"),
        )

    def _call_api(self, endpoint: str, payload: dict, log: Any) -> bytes:
        url = f"{self._base_url}{endpoint}"
        for attempt in range(1, self._max_retries + 1):
            try:
                resp = self._client.post(url, json=payload)
                resp.raise_for_status()
                return resp.content
            except httpx.TimeoutException as e:
                log.warning("qwen3_tts.timeout", attempt=attempt)
                if attempt == self._max_retries:
                    raise TTSTimeoutError(
                        f"Qwen3-TTS timed out after {self._max_retries} attempts",
                        module="tts.qwen3",
                    ) from e
            except httpx.HTTPError as e:
                log.warning("qwen3_tts.error", attempt=attempt, error=str(e))
                if attempt == self._max_retries:
                    raise TTSConnectionError(
                        f"Qwen3-TTS error: {e}",
                        module="tts.qwen3",
                    ) from e
        raise TTSConnectionError("Unreachable", module="tts.qwen3")

    def close(self) -> None:
        self._client.close()
