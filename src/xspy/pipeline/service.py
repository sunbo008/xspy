"""PipelineOrchestrator: coordinates all modules from novel to audiobook."""

from __future__ import annotations

import re
import time

import structlog

from xspy.core.config import XspySettings
from xspy.core.exceptions import PipelineError
from xspy.core.logging import new_trace_id
from xspy.core.models import (
    ChapterResult,
    CharacterInput,
    EmotionInput,
    ParseInput,
    PipelineInput,
    PipelineResult,
    PipelineStats,
    ScreenwriterInput,
    TaskState,
    VoiceBankInput,
)
from xspy.pipeline.persistence import IntermediatePersistence

logger = structlog.get_logger()


class PipelineOrchestrator:
    """Orchestrates the full novel-to-audiobook pipeline."""

    def __init__(
        self,
        settings: XspySettings,
        parser: object,
        screenwriter: object,
        character_engine: object,
        emotion_system: object,
        voice_bank: object,
        tts_client: object,
        audio_processor: object,
    ) -> None:
        self._settings = settings
        self._parser = parser
        self._screenwriter = screenwriter
        self._character_engine = character_engine
        self._emotion_system = emotion_system
        self._voice_bank = voice_bank
        self._tts_client = tts_client
        self._audio_processor = audio_processor
        self._persistence = IntermediatePersistence(settings.pipeline.intermediate_dir)

    def process(self, input: PipelineInput) -> PipelineResult:
        trace_id = new_trace_id()
        novel_slug = _slugify(input.novel_file.stem)
        start_time = time.monotonic()

        log = logger.bind(trace_id=trace_id, novel_slug=novel_slug)
        log.info("pipeline.start", file=str(input.novel_file))

        try:
            # Stage 1: Parse
            log.info("pipeline.stage", stage="parse")
            parse_result = self._parser.process(ParseInput(file_path=input.novel_file))
            self._persistence.save(
                novel_slug,
                "parse_result.json",
                parse_result,
                module="parser",
                trace_id=trace_id,
            )

            # Stage 2: Character Analysis
            log.info("pipeline.stage", stage="character")
            char_output = self._character_engine.process(CharacterInput(parse_result=parse_result))
            self._persistence.save(
                novel_slug,
                "cast_registry.json",
                char_output.cast_registry,
                module="character",
                trace_id=trace_id,
            )
            self._persistence.save(
                novel_slug,
                "relation_graph.json",
                char_output.relation_graph,
                module="character",
                trace_id=trace_id,
            )

            # Stage 3: Screenwriter
            log.info("pipeline.stage", stage="screenwriter")
            sw_output = self._screenwriter.process(
                ScreenwriterInput(
                    parse_result=parse_result,
                    cast_registry=char_output.cast_registry,
                    chapter_indices=input.chapter_indices,
                )
            )
            for ch_sp in sw_output.screenplay.chapters:
                self._persistence.save(
                    novel_slug,
                    f"screenplay/ch{ch_sp.chapter_index:03d}.json",
                    ch_sp,
                    module="screenwriter",
                    trace_id=trace_id,
                )

            # Stage 4: Emotion
            log.info("pipeline.stage", stage="emotion")
            enriched = self._emotion_system.process(
                EmotionInput(
                    screenplay=sw_output.screenplay,
                    cast_registry=char_output.cast_registry,
                )
            )
            for ch_sp in enriched.chapters:
                self._persistence.save(
                    novel_slug,
                    f"enriched_screenplay/ch{ch_sp.chapter_index:03d}.json",
                    ch_sp,
                    module="emotion",
                    trace_id=trace_id,
                )

            # Stage 5: Voice Assignment
            log.info("pipeline.stage", stage="voice_bank")
            voice_assignment = self._voice_bank.process(
                VoiceBankInput(cast_registry=char_output.cast_registry)
            )
            self._persistence.save(
                novel_slug,
                "voice_assignment.json",
                voice_assignment,
                module="voice_bank",
                trace_id=trace_id,
            )

            # Stage 6-7: TTS + Audio Assembly (placeholder for full implementation)
            log.info("pipeline.stage", stage="tts_audio")
            chapter_results = [
                ChapterResult(
                    chapter_index=ch.chapter_index,
                    status=TaskState.COMPLETED,
                )
                for ch in enriched.chapters
            ]

            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            log.info("pipeline.done", elapsed_ms=elapsed_ms)

            return PipelineResult(
                novel_slug=novel_slug,
                chapter_results=chapter_results,
                stats=PipelineStats(
                    total_duration_ms=elapsed_ms,
                    chapters_processed=len(chapter_results),
                ),
            )

        except PipelineError:
            raise
        except Exception as e:
            log.error("pipeline.failed", error=str(e))
            raise PipelineError(
                f"Pipeline failed: {e}",
                module="pipeline",
                context={"novel_slug": novel_slug, "trace_id": trace_id},
            ) from e


def _slugify(name: str) -> str:
    """Convert a novel name to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\u4e00-\u9fff-]", "_", name)
    return slug.strip("_")[:60] or "unnamed"
