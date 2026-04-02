"""Adapter: EmotionDetail → TTS engine-specific parameters.

Loads mapping from config/emotion_tts_mapping.yaml and converts
emotion annotations into parameters each TTS engine understands.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from xspy.core.models import EmotionDetail, TTSEmotionParams

_DEFAULT_MAPPING_PATH = Path("config/emotion_tts_mapping.yaml")


class EmotionTTSAdapter:
    """Converts EmotionDetail into TTS engine-specific parameters."""

    def __init__(self, mapping_path: str | Path = _DEFAULT_MAPPING_PATH) -> None:
        self._mapping: dict[str, dict[str, dict[str, Any]]] = {}
        path = Path(mapping_path)
        if path.exists():
            self._mapping = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def adapt(self, emotion: EmotionDetail, *, engine: str = "index-tts") -> TTSEmotionParams:
        """Convert emotion detail to TTS parameters for the given engine.

        Uses mapping table as base, then modulates by intensity.
        """
        engine_map = self._mapping.get(engine, {})
        emotion_params = engine_map.get(emotion.type.value, {})

        base_speed = float(emotion_params.get("speed", 1.0))
        base_pitch = float(emotion_params.get("pitch_shift", 0.0))
        base_energy = float(emotion_params.get("energy", 1.0))
        style = str(emotion_params.get("style", ""))

        intensity_factor = 0.5 + emotion.intensity * 0.5

        return TTSEmotionParams(
            speed=round(1.0 + (base_speed - 1.0) * intensity_factor, 3),
            pitch_shift=round(base_pitch * intensity_factor, 3),
            energy=round(1.0 + (base_energy - 1.0) * intensity_factor, 3),
            style=style,
        )

    def get_supported_engines(self) -> list[str]:
        return list(self._mapping.keys())
