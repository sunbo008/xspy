"""VoiceBankService: assigns voices to characters based on profiles."""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from xspy.core.models import (
    CastEntry,
    VoiceAssignment,
    VoiceBankInput,
    VoiceEntry,
)

logger = structlog.get_logger()

_DEFAULT_VOICE_TEMPLATES_DIR = Path("resources/voice_templates")


class VoiceBankService:
    """Assign TTS voices to characters based on their profiles."""

    def __init__(
        self,
        voice_templates_dir: str | Path = _DEFAULT_VOICE_TEMPLATES_DIR,
        narrator_voice_id: str = "narrator-default",
    ) -> None:
        self._templates_dir = Path(voice_templates_dir)
        self._narrator_voice_id = narrator_voice_id
        self._voice_catalog: list[dict] = self._load_catalog()

    def _load_catalog(self) -> list[dict]:
        catalog_path = self._templates_dir / "catalog.json"
        if catalog_path.exists():
            return json.loads(catalog_path.read_text(encoding="utf-8"))
        return []

    def process(self, input: VoiceBankInput) -> VoiceAssignment:
        cast = input.cast_registry
        existing = input.existing_assignments

        log = logger.bind(total_characters=len(cast.characters))
        log.info("voice_bank.start")

        assignments: dict[str, VoiceEntry] = {}
        unassigned: list[str] = []

        if existing:
            assignments.update(existing.assignments)

        assignments["narrator"] = VoiceEntry(
            voice_id=self._narrator_voice_id,
            speaker_id="narrator",
            display_name="旁白",
        )

        for char in cast.characters:
            if char.speaker_id in assignments:
                continue

            voice = self._match_voice(char)
            if voice:
                assignments[char.speaker_id] = voice
            else:
                unassigned.append(char.speaker_id)

        log.info(
            "voice_bank.done",
            assigned=len(assignments),
            unassigned=len(unassigned),
        )

        return VoiceAssignment(assignments=assignments, unassigned=unassigned)

    def _match_voice(self, char: CastEntry) -> VoiceEntry | None:
        """Find the best matching voice from catalog based on character profile."""
        if not self._voice_catalog:
            return self._generate_placeholder_voice(char)

        gender = char.profile.gender.lower() if char.profile.gender else ""
        age = char.profile.age_range.lower() if char.profile.age_range else ""

        best_match: dict | None = None
        best_score = -1

        for voice in self._voice_catalog:
            score = 0
            if gender and voice.get("gender", "").lower() == gender:
                score += 2
            if age and voice.get("age_range", "").lower() == age:
                score += 1
            if score > best_score:
                best_score = score
                best_match = voice

        if best_match:
            return VoiceEntry(
                voice_id=best_match["voice_id"],
                speaker_id=char.speaker_id,
                display_name=char.name,
                tts_engine=best_match.get("tts_engine", "index-tts"),
                reference_audio_path=best_match.get("reference_audio", ""),
            )

        return self._generate_placeholder_voice(char)

    @staticmethod
    def _generate_placeholder_voice(char: CastEntry) -> VoiceEntry:
        """Generate a placeholder voice assignment when no catalog match exists."""
        return VoiceEntry(
            voice_id=f"auto-{char.speaker_id}",
            speaker_id=char.speaker_id,
            display_name=char.name,
            tts_engine="index-tts",
        )
