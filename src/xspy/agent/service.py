"""ScreenwriterAgent: converts parsed chapters into structured screenplay."""

from __future__ import annotations

import structlog

from xspy.core.exceptions import AgentError
from xspy.core.llm.prompts import PromptManager
from xspy.core.llm.router import ModelRouter
from xspy.core.llm.validator import validate_json_output
from xspy.core.models import (
    CastEntry,
    CastRegistry,
    ChapterScreenplay,
    Screenplay,
    ScreenwriterInput,
    ScreenwriterOutput,
    SpeakerRole,
    Utterance,
)

logger = structlog.get_logger()

TASK_TYPE = "screenwriter"


class ScreenwriterService:
    """Convert novel chapters into structured screenplay via LLM."""

    def __init__(self, router: ModelRouter, prompts: PromptManager) -> None:
        self._router = router
        self._prompts = prompts

    def process(self, input: ScreenwriterInput) -> ScreenwriterOutput:
        chapters = input.parse_result.chapters
        cast_registry = input.cast_registry or CastRegistry()

        indices = input.chapter_indices or [ch.index for ch in chapters]
        chapter_screenplays: list[ChapterScreenplay] = []

        for ch in chapters:
            if ch.index not in indices:
                continue

            log = logger.bind(chapter_index=ch.index, chapter_title=ch.title)
            log.info("screenwriter.processing")

            prompt = self._prompts.render(
                "screenwriter/split.j2",
                chapter_text=ch.text,
                cast_registry=cast_registry if cast_registry.characters else None,
            )

            try:
                raw_response = self._router.chat(
                    TASK_TYPE,
                    [
                        {
                            "role": "system",
                            "content": "你是专业的有声书编剧。请严格按JSON格式输出。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                utterances_data = validate_json_output(raw_response, expected_type=list)
            except Exception as e:
                log.error("screenwriter.llm_failed", error=str(e))
                raise AgentError(
                    f"Screenwriter failed on chapter {ch.index}: {e}",
                    module="agent.screenwriter",
                    context={"chapter_index": ch.index},
                ) from e

            utterances = [
                Utterance(
                    id=u.get("id", f"u{i:04d}"),
                    speaker_id=u.get("speaker_id", "unknown"),
                    text=u.get("text", ""),
                    is_dialogue=u.get("is_dialogue", True),
                )
                for i, u in enumerate(utterances_data)
            ]

            self._update_cast_from_utterances(cast_registry, utterances)

            chapter_screenplays.append(
                ChapterScreenplay(
                    chapter_index=ch.index,
                    chapter_title=ch.title,
                    utterances=utterances,
                )
            )
            log.info("screenwriter.done", utterances=len(utterances))

        return ScreenwriterOutput(
            screenplay=Screenplay(chapters=chapter_screenplays),
            cast_registry=cast_registry,
        )

    @staticmethod
    def _update_cast_from_utterances(registry: CastRegistry, utterances: list[Utterance]) -> None:
        """Add newly discovered speakers to the cast registry."""
        known_ids = {c.speaker_id for c in registry.characters}
        for u in utterances:
            if u.speaker_id not in known_ids and u.speaker_id != "narrator":
                registry.characters.append(
                    CastEntry(
                        speaker_id=u.speaker_id,
                        name=u.speaker_id,
                        role_level=SpeakerRole.MINOR,
                    )
                )
                known_ids.add(u.speaker_id)
