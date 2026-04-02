"""Audio format normalizer — ensures consistent WAV format from TTS outputs."""

from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment


def normalize_audio(
    input_path: Path,
    *,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,  # 16-bit
) -> Path:
    """Normalize an audio file to standard WAV format.

    Converts to: 24kHz, 16-bit, mono WAV.
    Overwrites the input file in-place.
    """
    audio = AudioSegment.from_file(str(input_path))

    audio = audio.set_frame_rate(sample_rate)
    audio = audio.set_channels(channels)
    audio = audio.set_sample_width(sample_width)

    output_path = input_path.with_suffix(".wav")
    audio.export(str(output_path), format="wav")
    return output_path


def get_audio_info(file_path: Path) -> dict[str, int]:
    """Get basic audio file info."""
    audio = AudioSegment.from_file(str(file_path))
    return {
        "duration_ms": len(audio),
        "sample_rate": audio.frame_rate,
        "channels": audio.channels,
        "sample_width": audio.sample_width,
    }
