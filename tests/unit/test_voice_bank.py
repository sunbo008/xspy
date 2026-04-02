"""Unit tests for VoiceBankService."""

from __future__ import annotations

from xspy.core.models import (
    CastEntry,
    CastRegistry,
    CharacterProfile,
    SpeakerRole,
    VoiceAssignment,
    VoiceBankInput,
)
from xspy.voice.service import VoiceBankService


class TestVoiceBankService:
    def test_narrator_always_assigned(self):
        svc = VoiceBankService()
        result = svc.process(VoiceBankInput(cast_registry=CastRegistry()))
        assert "narrator" in result.assignments

    def test_assigns_placeholder_voices(self):
        registry = CastRegistry(
            characters=[
                CastEntry(
                    speaker_id="hero",
                    name="英雄",
                    role_level=SpeakerRole.PROTAGONIST,
                    profile=CharacterProfile(gender="男", age_range="青年"),
                ),
                CastEntry(
                    speaker_id="heroine",
                    name="女主",
                    role_level=SpeakerRole.SUPPORTING,
                    profile=CharacterProfile(gender="女", age_range="青年"),
                ),
            ]
        )
        svc = VoiceBankService()
        result = svc.process(VoiceBankInput(cast_registry=registry))
        assert "hero" in result.assignments
        assert "heroine" in result.assignments
        assert result.assignments["hero"].voice_id.startswith("auto-")

    def test_preserves_existing_assignments(self):
        from xspy.core.models import VoiceEntry

        registry = CastRegistry(
            characters=[
                CastEntry(speaker_id="hero", name="英雄"),
            ]
        )
        existing = VoiceAssignment(
            assignments={
                "hero": VoiceEntry(voice_id="custom-v1", speaker_id="hero"),
            }
        )
        svc = VoiceBankService()
        result = svc.process(VoiceBankInput(cast_registry=registry, existing_assignments=existing))
        assert result.assignments["hero"].voice_id == "custom-v1"
