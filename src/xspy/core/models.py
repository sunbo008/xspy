"""Shared Pydantic data models used across all xspy modules."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Meta header for intermediate data persistence
# ---------------------------------------------------------------------------


class IntermediateMetaHeader(BaseModel):
    """Metadata header included in every persisted intermediate JSON file."""

    module: str
    schema_version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.now)
    trace_id: str = ""


# ---------------------------------------------------------------------------
# Emotion taxonomy (20 types)
# ---------------------------------------------------------------------------


class EmotionType(StrEnum):
    """20-category emotion taxonomy with VAD defaults."""

    NEUTRAL = "neutral"
    JOYFUL = "joyful"
    SORROWFUL = "sorrowful"
    FURIOUS = "furious"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    CONTEMPTUOUS = "contemptuous"
    ANXIOUS = "anxious"
    SERENE = "serene"
    TENDER = "tender"
    PROUD = "proud"
    ASHAMED = "ashamed"
    ENVIOUS = "envious"
    CURIOUS = "curious"
    AMUSED = "amused"
    IRRITATED = "irritated"
    TENSE = "tense"
    PAINED = "pained"
    PLAYFUL = "playful"

    @property
    def vad_default(self) -> tuple[float, float, float]:
        """Return default (valence, arousal, dominance) vector."""
        return _VAD_DEFAULTS.get(self, (0.5, 0.5, 0.5))


_VAD_DEFAULTS: dict[EmotionType, tuple[float, float, float]] = {
    EmotionType.NEUTRAL: (0.5, 0.3, 0.5),
    EmotionType.JOYFUL: (0.9, 0.7, 0.6),
    EmotionType.SORROWFUL: (0.1, 0.3, 0.3),
    EmotionType.FURIOUS: (0.1, 0.9, 0.7),
    EmotionType.FEARFUL: (0.1, 0.8, 0.2),
    EmotionType.SURPRISED: (0.6, 0.7, 0.4),
    EmotionType.DISGUSTED: (0.2, 0.5, 0.6),
    EmotionType.CONTEMPTUOUS: (0.2, 0.4, 0.8),
    EmotionType.ANXIOUS: (0.3, 0.7, 0.3),
    EmotionType.SERENE: (0.8, 0.2, 0.5),
    EmotionType.TENDER: (0.8, 0.3, 0.4),
    EmotionType.PROUD: (0.8, 0.5, 0.8),
    EmotionType.ASHAMED: (0.2, 0.4, 0.2),
    EmotionType.ENVIOUS: (0.3, 0.5, 0.4),
    EmotionType.CURIOUS: (0.7, 0.6, 0.5),
    EmotionType.AMUSED: (0.8, 0.6, 0.5),
    EmotionType.IRRITATED: (0.3, 0.6, 0.6),
    EmotionType.TENSE: (0.3, 0.7, 0.4),
    EmotionType.PAINED: (0.1, 0.6, 0.3),
    EmotionType.PLAYFUL: (0.8, 0.7, 0.5),
}


class SpeakerRole(StrEnum):
    """Character importance level."""

    PROTAGONIST = "protagonist"
    SUPPORTING = "supporting"
    MINOR = "minor"
    NARRATOR = "narrator"


class TaskState(StrEnum):
    """Pipeline task execution state."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Novel parsing models
# ---------------------------------------------------------------------------


class NovelMetadata(BaseModel):
    """Metadata extracted from a novel file."""

    title: str = ""
    author: str = ""
    total_word_count: int = 0
    source_format: str = ""
    file_hash: str = ""


class Chapter(BaseModel):
    """A single chapter extracted from a novel."""

    index: int
    title: str = ""
    text: str
    word_count: int = 0


class ParseInput(BaseModel):
    """Input for the NovelParser module."""

    file_path: Path
    encoding_override: str | None = None
    chapter_pattern_override: str | None = None


class ParseResult(BaseModel):
    """Output of the NovelParser module."""

    metadata: NovelMetadata
    chapters: list[Chapter]
    _meta: IntermediateMetaHeader | None = None


# ---------------------------------------------------------------------------
# Screenwriter / Agent models
# ---------------------------------------------------------------------------


class Paraverbal(BaseModel):
    """A paraverbal sound effect attached to an utterance."""

    type: str  # sigh, laughter, gasp, etc.
    position: str = "before"  # before | after | replace


class EmotionDetail(BaseModel):
    """Rich emotion annotation for a single utterance."""

    type: EmotionType = EmotionType.NEUTRAL
    vad: tuple[float, float, float] = (0.5, 0.3, 0.5)
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    tts_params: dict[str, dict[str, Any]] = Field(default_factory=dict)


class Utterance(BaseModel):
    """A single speech unit in a screenplay."""

    id: str
    speaker_id: str
    text: str
    is_dialogue: bool = True
    emotion_type: EmotionType = EmotionType.NEUTRAL
    emotion_detail: EmotionDetail | None = None
    paraverbals: list[Paraverbal] = Field(default_factory=list)


class ChapterScreenplay(BaseModel):
    """Screenplay for one chapter."""

    chapter_index: int
    chapter_title: str = ""
    utterances: list[Utterance]


class Screenplay(BaseModel):
    """Complete screenplay for a novel."""

    chapters: list[ChapterScreenplay]


class ScreenwriterInput(BaseModel):
    """Input for the ScreenwriterAgent module."""

    parse_result: ParseResult
    cast_registry: CastRegistry | None = None
    chapter_indices: list[int] | None = None


class ScreenwriterOutput(BaseModel):
    """Output of the ScreenwriterAgent module."""

    screenplay: Screenplay
    cast_registry: CastRegistry
    _meta: IntermediateMetaHeader | None = None


# ---------------------------------------------------------------------------
# Character engine models
# ---------------------------------------------------------------------------


class CharacterProfile(BaseModel):
    """Inferred character attributes."""

    gender: str = ""
    age_range: str = ""
    profession: str = ""
    personality: str = ""
    speech_style: str = ""
    emotional_baseline: EmotionType = EmotionType.NEUTRAL
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class CastEntry(BaseModel):
    """A single character in the cast registry."""

    speaker_id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    role_level: SpeakerRole = SpeakerRole.MINOR
    profile: CharacterProfile = Field(default_factory=CharacterProfile)
    voice_description: str = ""


class CastRegistry(BaseModel):
    """Registry of all characters in a novel."""

    characters: list[CastEntry] = Field(default_factory=list)


class RelationEdge(BaseModel):
    """A relationship between two characters."""

    from_id: str
    to_id: str
    relation_type: str
    description: str = ""


class RelationGraph(BaseModel):
    """Character relationship graph."""

    edges: list[RelationEdge] = Field(default_factory=list)


class CharacterInput(BaseModel):
    """Input for the CharacterEngine module."""

    parse_result: ParseResult
    cast_registry: CastRegistry | None = None


class CharacterOutput(BaseModel):
    """Output of the CharacterEngine module."""

    cast_registry: CastRegistry
    relation_graph: RelationGraph
    _meta: IntermediateMetaHeader | None = None


# ---------------------------------------------------------------------------
# Emotion system models
# ---------------------------------------------------------------------------


class EmotionInput(BaseModel):
    """Input for the EmotionSystem module."""

    screenplay: Screenplay
    cast_registry: CastRegistry
    chapter_index: int | None = None


class EnrichedScreenplay(BaseModel):
    """Screenplay with emotion_detail fully populated."""

    chapters: list[ChapterScreenplay]
    _meta: IntermediateMetaHeader | None = None


# ---------------------------------------------------------------------------
# Voice bank models
# ---------------------------------------------------------------------------


class VoiceEntry(BaseModel):
    """Voice configuration for one character."""

    voice_id: str
    speaker_id: str
    display_name: str = ""
    tts_engine: str = "index-tts"
    reference_audio_path: str = ""
    engine_params: dict[str, Any] = Field(default_factory=dict)


class VoiceBankInput(BaseModel):
    """Input for the VoiceBank module."""

    cast_registry: CastRegistry
    existing_assignments: VoiceAssignment | None = None


class VoiceAssignment(BaseModel):
    """Voice assignments for all characters."""

    assignments: dict[str, VoiceEntry] = Field(default_factory=dict)
    unassigned: list[str] = Field(default_factory=list)
    _meta: IntermediateMetaHeader | None = None


# ---------------------------------------------------------------------------
# TTS models
# ---------------------------------------------------------------------------


class TTSEmotionParams(BaseModel):
    """TTS engine-specific emotion parameters."""

    speed: float = 1.0
    pitch_shift: float = 0.0
    energy: float = 1.0
    style: str = ""


class TTSRequest(BaseModel):
    """Input for a single TTS synthesis call."""

    text: str
    voice_id: str
    reference_audio_path: str = ""
    emotion_params: TTSEmotionParams | None = None
    tts_engine: str = "index-tts"
    engine_params: dict[str, Any] = Field(default_factory=dict)


class TTSMetadata(BaseModel):
    """Metadata from a TTS synthesis call."""

    latency_ms: int = 0
    model_name: str = ""
    request_id: str = ""


class TTSResponse(BaseModel):
    """Output of a single TTS synthesis call."""

    audio_path: Path | None = None
    duration_ms: int = 0
    sample_rate: int = 24000
    engine_used: str = ""
    metadata: TTSMetadata = Field(default_factory=TTSMetadata)
    _meta: IntermediateMetaHeader | None = None


# ---------------------------------------------------------------------------
# Audio processor models
# ---------------------------------------------------------------------------


class AudioSegment(BaseModel):
    """Reference to a single utterance audio file."""

    utterance_id: str
    file_path: Path
    duration_ms: int = 0


class AudioProcessingConfig(BaseModel):
    """Configuration for audio post-processing."""

    dialogue_silence_ms: int = 300
    narration_silence_ms: int = 500
    normalization_lufs: float = -16.0
    fade_in_ms: int = 1000
    fade_out_ms: int = 2000


class UtteranceMarker(BaseModel):
    """Timestamp marker for one utterance in assembled chapter audio."""

    utterance_id: str
    start_ms: int
    end_ms: int


class AudioInput(BaseModel):
    """Input for the AudioProcessor module."""

    segments: list[AudioSegment]
    screenplay: ChapterScreenplay
    voice_assignment: VoiceAssignment | None = None
    config: AudioProcessingConfig = Field(default_factory=AudioProcessingConfig)


class ChapterAudio(BaseModel):
    """Output of chapter audio assembly."""

    file_path: Path
    duration_ms: int = 0
    chapter_index: int = 0
    chapter_title: str = ""
    utterance_markers: list[UtteranceMarker] = Field(default_factory=list)
    _meta: IntermediateMetaHeader | None = None


class ChapterMarker(BaseModel):
    """Chapter marker for M4B audiobook."""

    title: str
    start_ms: int


class AudioBookMetadata(BaseModel):
    """Metadata for the final audiobook."""

    title: str = ""
    author: str = ""
    cover_image_path: str = ""


class AudioBook(BaseModel):
    """Final audiobook output."""

    file_path: Path
    chapters: list[ChapterMarker] = Field(default_factory=list)
    total_duration_ms: int = 0
    metadata: AudioBookMetadata = Field(default_factory=AudioBookMetadata)


# ---------------------------------------------------------------------------
# Pipeline models
# ---------------------------------------------------------------------------


class ChapterResult(BaseModel):
    """Per-chapter processing result."""

    chapter_index: int
    status: TaskState = TaskState.PENDING
    intermediate_files: dict[str, str] = Field(default_factory=dict)
    error_message: str = ""


class PipelineStats(BaseModel):
    """Pipeline execution statistics."""

    total_duration_ms: int = 0
    chapters_processed: int = 0
    tts_calls_made: int = 0
    llm_calls_made: int = 0
    cache_hit_rate: float = 0.0


class PipelineInput(BaseModel):
    """Input for the PipelineOrchestrator."""

    novel_file: Path
    config_overrides: dict[str, Any] | None = None
    resume_from_checkpoint: bool = True
    chapter_indices: list[int] | None = None
    force_stages: list[str] | None = None


class PipelineResult(BaseModel):
    """Output of the PipelineOrchestrator."""

    novel_slug: str = ""
    audiobook: AudioBook | None = None
    chapter_results: list[ChapterResult] = Field(default_factory=list)
    stats: PipelineStats = Field(default_factory=PipelineStats)
    _meta: IntermediateMetaHeader | None = None


# Forward reference resolution
ScreenwriterInput.model_rebuild()
ScreenwriterOutput.model_rebuild()
VoiceBankInput.model_rebuild()
