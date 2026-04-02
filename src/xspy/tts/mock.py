"""MockTTSEngine — deterministic silence WAV for testing.

Returns silence audio proportional to text length,
ensuring deterministic test results without a real TTS server.
"""

from __future__ import annotations

import struct
from pathlib import Path

from xspy.core.models import TTSMetadata, TTSRequest, TTSResponse

_SAMPLE_RATE = 24000
_MS_PER_CHAR = 100


class MockTTSEngine:
    """Deterministic mock TTS that generates silence WAV files."""

    def __init__(self, output_dir: str | Path = "data/tts_mock") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._call_count = 0

    def process(self, input: TTSRequest) -> TTSResponse:
        self._call_count += 1
        duration_ms = len(input.text) * _MS_PER_CHAR
        num_samples = int(_SAMPLE_RATE * duration_ms / 1000)

        output_path = self._output_dir / f"mock_{self._call_count:06d}.wav"
        _write_silent_wav(output_path, num_samples, _SAMPLE_RATE)

        return TTSResponse(
            audio_path=output_path,
            duration_ms=duration_ms,
            sample_rate=_SAMPLE_RATE,
            engine_used="mock",
            metadata=TTSMetadata(latency_ms=1, model_name="mock-tts"),
        )

    @property
    def call_count(self) -> int:
        return self._call_count


def _write_silent_wav(path: Path, num_samples: int, sample_rate: int) -> None:
    """Write a silent 16-bit mono WAV file."""
    data_size = num_samples * 2  # 16-bit = 2 bytes/sample
    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # chunk size
        f.write(struct.pack("<H", 1))  # PCM
        f.write(struct.pack("<H", 1))  # mono
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * 2))  # byte rate
        f.write(struct.pack("<H", 2))  # block align
        f.write(struct.pack("<H", 16))  # bits per sample
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)
