"""AudioProcessorService: assembles utterance audio into chapters and audiobooks."""

from __future__ import annotations

from pathlib import Path

import structlog
from pydub import AudioSegment as PydubSegment

from xspy.core.exceptions import AudioError
from xspy.core.models import (
    AudioBook,
    AudioBookMetadata,
    AudioInput,
    AudioProcessingConfig,
    ChapterAudio,
    ChapterMarker,
    UtteranceMarker,
)

logger = structlog.get_logger()


class AudioProcessorService:
    """Assemble individual utterance audio files into chapter and book audio."""

    def __init__(self, output_dir: str | Path = "data/output") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def process(self, input: AudioInput) -> ChapterAudio:
        config = input.config
        segments = input.segments
        screenplay = input.screenplay

        log = logger.bind(
            chapter_index=screenplay.chapter_index,
            segment_count=len(segments),
        )
        log.info("audio.assembling")

        if not segments:
            raise AudioError(
                "No audio segments to assemble",
                module="audio",
                context={"chapter_index": screenplay.chapter_index},
            )

        combined = PydubSegment.empty()
        markers: list[UtteranceMarker] = []
        segment_map = {s.utterance_id: s for s in segments}

        for utt in screenplay.utterances:
            seg = segment_map.get(utt.id)
            if not seg:
                log.warning("audio.segment_missing", utterance_id=utt.id)
                continue

            if not seg.file_path.exists():
                log.warning("audio.file_missing", path=str(seg.file_path))
                continue

            audio = PydubSegment.from_file(str(seg.file_path))

            start_ms = len(combined)

            silence_ms = (
                config.dialogue_silence_ms if utt.is_dialogue else config.narration_silence_ms
            )
            if len(combined) > 0:
                combined += PydubSegment.silent(duration=silence_ms)

            combined += audio

            markers.append(
                UtteranceMarker(
                    utterance_id=utt.id,
                    start_ms=start_ms + silence_ms if start_ms > 0 else 0,
                    end_ms=len(combined),
                )
            )

        combined = self._normalize(combined, config)

        chapter_file = self._output_dir / f"ch{screenplay.chapter_index:03d}.wav"
        combined.export(str(chapter_file), format="wav")

        log.info("audio.done", duration_ms=len(combined))

        return ChapterAudio(
            file_path=chapter_file,
            duration_ms=len(combined),
            chapter_index=screenplay.chapter_index,
            chapter_title=screenplay.chapter_title,
            utterance_markers=markers,
        )

    def assemble_audiobook(self, chapters: list[ChapterAudio]) -> AudioBook:
        """Combine chapter audio files into a single audiobook."""
        log = logger.bind(chapters=len(chapters))
        log.info("audiobook.assembling")

        chapters_sorted = sorted(chapters, key=lambda c: c.chapter_index)

        combined = PydubSegment.empty()
        chapter_markers: list[ChapterMarker] = []

        for ch in chapters_sorted:
            if not ch.file_path.exists():
                log.warning("audiobook.chapter_missing", chapter_index=ch.chapter_index)
                continue

            chapter_markers.append(
                ChapterMarker(
                    title=ch.chapter_title or f"Chapter {ch.chapter_index + 1}",
                    start_ms=len(combined),
                )
            )

            audio = PydubSegment.from_file(str(ch.file_path))
            combined += audio

        output_path = self._output_dir / "audiobook.m4b"
        combined.export(
            str(output_path),
            format="ipod",
            codec="aac",
            bitrate="128k",
        )

        log.info("audiobook.done", total_ms=len(combined))

        return AudioBook(
            file_path=output_path,
            chapters=chapter_markers,
            total_duration_ms=len(combined),
            metadata=AudioBookMetadata(),
        )

    @staticmethod
    def _normalize(audio: PydubSegment, config: AudioProcessingConfig) -> PydubSegment:
        """Apply loudness normalization."""
        target_dbfs = config.normalization_lufs
        change_db = target_dbfs - audio.dBFS
        return audio.apply_gain(change_db)
