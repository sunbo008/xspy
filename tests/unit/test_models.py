"""Unit tests for core/models.py — serialization, validation, enum metadata."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from xspy.core.models import (
    AudioProcessingConfig,
    CastEntry,
    CastRegistry,
    Chapter,
    ChapterScreenplay,
    EmotionDetail,
    EmotionType,
    IntermediateMetaHeader,
    NovelMetadata,
    Paraverbal,
    ParseInput,
    ParseResult,
    PipelineInput,
    Screenplay,
    ScreenwriterInput,
    SpeakerRole,
    TaskState,
    TTSRequest,
    Utterance,
    VoiceAssignment,
    VoiceEntry,
)


class TestEmotionType:
    def test_all_20_types_defined(self):
        assert len(EmotionType) == 20

    def test_vad_defaults_exist_for_all(self):
        for et in EmotionType:
            v, a, d = et.vad_default
            assert 0.0 <= v <= 1.0
            assert 0.0 <= a <= 1.0
            assert 0.0 <= d <= 1.0

    def test_neutral_vad(self):
        assert EmotionType.NEUTRAL.vad_default == (0.5, 0.3, 0.5)

    def test_string_value(self):
        assert EmotionType.JOYFUL.value == "joyful"
        assert EmotionType("furious") is EmotionType.FURIOUS


class TestSpeakerRole:
    def test_all_roles(self):
        assert len(SpeakerRole) == 4
        assert SpeakerRole.NARRATOR.value == "narrator"


class TestTaskState:
    def test_all_states(self):
        assert len(TaskState) == 5


class TestIntermediateMetaHeader:
    def test_defaults(self):
        meta = IntermediateMetaHeader(module="parser")
        assert meta.module == "parser"
        assert meta.schema_version == "0.1.0"
        assert meta.trace_id == ""
        assert meta.timestamp is not None

    def test_roundtrip(self):
        meta = IntermediateMetaHeader(module="emotion", trace_id="abc123")
        data = meta.model_dump_json()
        restored = IntermediateMetaHeader.model_validate_json(data)
        assert restored.module == "emotion"
        assert restored.trace_id == "abc123"


class TestChapter:
    def test_basic(self):
        ch = Chapter(index=0, title="第一章", text="正文内容", word_count=4)
        assert ch.index == 0
        assert ch.word_count == 4

    def test_empty_title(self):
        ch = Chapter(index=1, text="content")
        assert ch.title == ""


class TestParseResult:
    def test_roundtrip(self):
        result = ParseResult(
            metadata=NovelMetadata(title="测试小说", author="作者"),
            chapters=[Chapter(index=0, text="第一章正文")],
        )
        data = result.model_dump_json()
        restored = ParseResult.model_validate_json(data)
        assert restored.metadata.title == "测试小说"
        assert len(restored.chapters) == 1


class TestUtterance:
    def test_with_emotion(self):
        u = Utterance(
            id="u001",
            speaker_id="char01",
            text="你好",
            emotion_type=EmotionType.JOYFUL,
            emotion_detail=EmotionDetail(
                type=EmotionType.JOYFUL,
                vad=(0.9, 0.7, 0.6),
                intensity=0.8,
            ),
        )
        assert u.emotion_detail is not None
        assert u.emotion_detail.intensity == 0.8

    def test_with_paraverbal(self):
        u = Utterance(
            id="u002",
            speaker_id="char01",
            text="算了吧",
            paraverbals=[Paraverbal(type="sigh", position="before")],
        )
        assert len(u.paraverbals) == 1
        assert u.paraverbals[0].type == "sigh"


class TestEmotionDetail:
    def test_intensity_bounds(self):
        with pytest.raises(ValidationError):
            EmotionDetail(intensity=1.5)
        with pytest.raises(ValidationError):
            EmotionDetail(intensity=-0.1)

    def test_defaults(self):
        ed = EmotionDetail()
        assert ed.type == EmotionType.NEUTRAL
        assert ed.intensity == 0.5


class TestCastRegistry:
    def test_empty(self):
        cr = CastRegistry()
        assert cr.characters == []

    def test_with_entries(self):
        cr = CastRegistry(
            characters=[
                CastEntry(
                    speaker_id="c01",
                    name="林凡",
                    role_level=SpeakerRole.PROTAGONIST,
                ),
                CastEntry(
                    speaker_id="c02",
                    name="云梦",
                    aliases=["梦儿"],
                    role_level=SpeakerRole.SUPPORTING,
                ),
            ]
        )
        assert len(cr.characters) == 2
        assert cr.characters[1].aliases == ["梦儿"]


class TestScreenplay:
    def test_roundtrip(self):
        sp = Screenplay(
            chapters=[
                ChapterScreenplay(
                    chapter_index=0,
                    chapter_title="序章",
                    utterances=[
                        Utterance(id="u001", speaker_id="narrator", text="在一个..."),
                    ],
                )
            ]
        )
        data = sp.model_dump_json()
        restored = Screenplay.model_validate_json(data)
        assert len(restored.chapters) == 1
        assert restored.chapters[0].utterances[0].text == "在一个..."


class TestVoiceEntry:
    def test_basic(self):
        ve = VoiceEntry(voice_id="v01", speaker_id="c01", tts_engine="index-tts")
        assert ve.voice_id == "v01"


class TestVoiceAssignment:
    def test_with_assignments(self):
        va = VoiceAssignment(
            assignments={
                "c01": VoiceEntry(voice_id="v01", speaker_id="c01"),
            },
            unassigned=["c99"],
        )
        data = va.model_dump_json()
        restored = VoiceAssignment.model_validate_json(data)
        assert "c01" in restored.assignments
        assert "c99" in restored.unassigned


class TestTTSRequest:
    def test_minimal(self):
        req = TTSRequest(text="你好世界", voice_id="v01")
        assert req.tts_engine == "index-tts"


class TestAudioProcessingConfig:
    def test_defaults(self):
        cfg = AudioProcessingConfig()
        assert cfg.normalization_lufs == -16.0
        assert cfg.dialogue_silence_ms == 300


class TestParseInput:
    def test_basic(self):
        pi = ParseInput(file_path=Path("/tmp/novel.txt"))
        assert pi.encoding_override is None


class TestScreenwriterInput:
    def test_with_optional_cast(self):
        pr = ParseResult(metadata=NovelMetadata(), chapters=[Chapter(index=0, text="text")])
        si = ScreenwriterInput(parse_result=pr)
        assert si.cast_registry is None


class TestPipelineInput:
    def test_defaults(self):
        pi = PipelineInput(novel_file=Path("/tmp/novel.txt"))
        assert pi.resume_from_checkpoint is True
        assert pi.chapter_indices is None
