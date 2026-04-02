"""Protocol definitions for all xspy module interfaces.

Each module communicates through these Protocols — implementations are
registered in the DI container and can be swapped without changing consumers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from xspy.core.models import (
        AudioBook,
        AudioInput,
        ChapterAudio,
        CharacterInput,
        CharacterOutput,
        EmotionInput,
        EnrichedScreenplay,
        ParseInput,
        ParseResult,
        PipelineInput,
        PipelineResult,
        ScreenwriterInput,
        ScreenwriterOutput,
        TTSRequest,
        TTSResponse,
        VoiceAssignment,
        VoiceBankInput,
    )


class NovelParserProtocol(Protocol):
    def process(self, input: ParseInput) -> ParseResult: ...


class ScreenwriterProtocol(Protocol):
    def process(self, input: ScreenwriterInput) -> ScreenwriterOutput: ...


class CharacterProtocol(Protocol):
    def process(self, input: CharacterInput) -> CharacterOutput: ...


class EmotionProtocol(Protocol):
    def process(self, input: EmotionInput) -> EnrichedScreenplay: ...


class VoiceBankProtocol(Protocol):
    def process(self, input: VoiceBankInput) -> VoiceAssignment: ...


class TTSEngineProtocol(Protocol):
    def process(self, input: TTSRequest) -> TTSResponse: ...


class AudioProcessorProtocol(Protocol):
    def process(self, input: AudioInput) -> ChapterAudio: ...
    def assemble_audiobook(self, chapters: list[ChapterAudio]) -> AudioBook: ...


class PipelineProtocol(Protocol):
    def process(self, input: PipelineInput) -> PipelineResult: ...
