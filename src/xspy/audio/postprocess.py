"""Audio post-processing: normalization, fade, noise gate."""

from __future__ import annotations

from pydub import AudioSegment

from xspy.core.models import AudioProcessingConfig


def normalize_loudness(audio: AudioSegment, target_lufs: float = -16.0) -> AudioSegment:
    """Normalize audio loudness to target LUFS (approximated via dBFS)."""
    if audio.dBFS == float("-inf"):
        return audio
    change_db = target_lufs - audio.dBFS
    return audio.apply_gain(change_db)


def apply_fade(
    audio: AudioSegment,
    *,
    fade_in_ms: int = 1000,
    fade_out_ms: int = 2000,
) -> AudioSegment:
    """Apply fade-in and fade-out to audio."""
    fade_in_ms = min(fade_in_ms, len(audio) // 2)
    fade_out_ms = min(fade_out_ms, len(audio) // 2)
    return audio.fade_in(fade_in_ms).fade_out(fade_out_ms)


def insert_silence(duration_ms: int) -> AudioSegment:
    """Create a silence segment of given duration."""
    return AudioSegment.silent(duration=duration_ms)


def postprocess_chapter(
    audio: AudioSegment,
    config: AudioProcessingConfig,
) -> AudioSegment:
    """Apply full post-processing chain to a chapter audio."""
    audio = normalize_loudness(audio, config.normalization_lufs)
    audio = apply_fade(
        audio,
        fade_in_ms=config.fade_in_ms,
        fade_out_ms=config.fade_out_ms,
    )
    return audio
