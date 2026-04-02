"""EmotionService: infers emotion for each utterance via LLM."""

from __future__ import annotations

import structlog

from xspy.core.llm.prompts import PromptManager
from xspy.core.llm.router import ModelRouter
from xspy.core.llm.validator import validate_json_output
from xspy.core.models import (
    CastRegistry,
    ChapterScreenplay,
    EmotionDetail,
    EmotionInput,
    EmotionType,
    EnrichedScreenplay,
    Paraverbal,
    Utterance,
)

logger = structlog.get_logger()

TASK_TYPE = "emotion-inference"
_BATCH_SIZE = 20


class EmotionService:
    """Infer emotions for all utterances in a screenplay."""

    def __init__(self, router: ModelRouter, prompts: PromptManager) -> None:
        self._router = router
        self._prompts = prompts

    def process(self, input: EmotionInput) -> EnrichedScreenplay:
        cast_registry = input.cast_registry
        chapters = input.screenplay.chapters
        target_idx = input.chapter_index

        enriched_chapters: list[ChapterScreenplay] = []

        for chapter in chapters:
            if target_idx is not None and chapter.chapter_index != target_idx:
                enriched_chapters.append(chapter)
                continue

            log = logger.bind(chapter_index=chapter.chapter_index)
            log.info("emotion.processing", utterances=len(chapter.utterances))

            enriched_utts = self._process_chapter(chapter.utterances, cast_registry, log)

            enriched_chapters.append(
                ChapterScreenplay(
                    chapter_index=chapter.chapter_index,
                    chapter_title=chapter.chapter_title,
                    utterances=enriched_utts,
                )
            )
            log.info("emotion.done")

        return EnrichedScreenplay(chapters=enriched_chapters)

    def _process_chapter(
        self,
        utterances: list[Utterance],
        cast_registry: CastRegistry,
        log: structlog.BoundLogger,
    ) -> list[Utterance]:
        """Process utterances in batches."""
        emotion_map: dict[str, dict] = {}

        for batch_start in range(0, len(utterances), _BATCH_SIZE):
            batch = utterances[batch_start : batch_start + _BATCH_SIZE]

            cast_info = cast_registry.characters if cast_registry.characters else None
            prompt = self._prompts.render(
                "emotion_inference/infer.j2",
                utterances=batch,
                cast_info=cast_info,
            )

            try:
                raw = self._router.chat(
                    TASK_TYPE,
                    [
                        {"role": "system", "content": "你是情感分析专家。请严格按JSON格式输出。"},
                        {"role": "user", "content": prompt},
                    ],
                )
                results = validate_json_output(raw, expected_type=list)
            except Exception as e:
                log.warning("emotion.batch_failed", error=str(e), batch_start=batch_start)
                continue

            for item in results:
                emotion_map[item.get("id", "")] = item

        enriched: list[Utterance] = []
        for u in utterances:
            emo_data = emotion_map.get(u.id)
            if emo_data:
                enriched.append(self._apply_emotion(u, emo_data))
            else:
                enriched.append(u)

        return enriched

    @staticmethod
    def _apply_emotion(utterance: Utterance, emo_data: dict) -> Utterance:
        """Apply LLM emotion analysis to an utterance."""
        emotion_str = emo_data.get("emotion_type", "neutral")
        try:
            emotion_type = EmotionType(emotion_str)
        except ValueError:
            emotion_type = EmotionType.NEUTRAL

        intensity = float(emo_data.get("intensity", 0.5))
        intensity = max(0.0, min(1.0, intensity))

        paraverbals = [
            Paraverbal(
                type=p.get("type", ""),
                position=p.get("position", "before"),
            )
            for p in emo_data.get("paraverbals", [])
        ]

        return utterance.model_copy(
            update={
                "emotion_type": emotion_type,
                "emotion_detail": EmotionDetail(
                    type=emotion_type,
                    vad=emotion_type.vad_default,
                    intensity=intensity,
                ),
                "paraverbals": paraverbals,
            }
        )
