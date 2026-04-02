"""CharacterEngine: infers character attributes and relationship graph via LLM."""

from __future__ import annotations

import structlog

from xspy.core.exceptions import AgentError
from xspy.core.llm.prompts import PromptManager
from xspy.core.llm.router import ModelRouter
from xspy.core.llm.validator import validate_json_output
from xspy.core.models import (
    CastEntry,
    CastRegistry,
    CharacterInput,
    CharacterOutput,
    CharacterProfile,
    EmotionType,
    RelationEdge,
    RelationGraph,
    SpeakerRole,
)

logger = structlog.get_logger()

TASK_TYPE = "character-analysis"
_SAMPLE_CHAPTERS = 5


class CharacterEngineService:
    """Analyze and infer character profiles and relationships."""

    def __init__(self, router: ModelRouter, prompts: PromptManager) -> None:
        self._router = router
        self._prompts = prompts

    def process(self, input: CharacterInput) -> CharacterOutput:
        chapters = input.parse_result.chapters
        sample = chapters[:_SAMPLE_CHAPTERS]

        log = logger.bind(total_chapters=len(chapters), sample_chapters=len(sample))
        log.info("character_engine.start")

        prompt = self._prompts.render(
            "character_analysis/analyze.j2",
            title=input.parse_result.metadata.title,
            total_chapters=len(chapters),
            sample_chapters=len(sample),
            chapters=sample,
        )

        try:
            raw = self._router.chat(
                TASK_TYPE,
                [
                    {"role": "system", "content": "你是专业的小说分析师。请严格按JSON格式输出。"},
                    {"role": "user", "content": prompt},
                ],
            )
            data = validate_json_output(
                raw,
                expected_type=dict,
                required_fields=["characters"],
            )
        except Exception as e:
            log.error("character_engine.llm_failed", error=str(e))
            raise AgentError(
                f"Character analysis failed: {e}",
                module="character",
            ) from e

        cast_entries = [self._parse_character(c) for c in data.get("characters", [])]

        if input.cast_registry:
            cast_entries = self._merge_registries(input.cast_registry.characters, cast_entries)

        relation_edges = [
            RelationEdge(
                from_id=r.get("from_id", ""),
                to_id=r.get("to_id", ""),
                relation_type=r.get("relation_type", ""),
                description=r.get("description", ""),
            )
            for r in data.get("relations", [])
        ]

        log.info(
            "character_engine.done", characters=len(cast_entries), relations=len(relation_edges)
        )

        return CharacterOutput(
            cast_registry=CastRegistry(characters=cast_entries),
            relation_graph=RelationGraph(edges=relation_edges),
        )

    @staticmethod
    def _parse_character(data: dict) -> CastEntry:
        profile_data = data.get("profile", {})
        baseline_str = profile_data.get("emotional_baseline", "neutral")
        try:
            baseline = EmotionType(baseline_str)
        except ValueError:
            baseline = EmotionType.NEUTRAL

        role_str = data.get("role_level", "minor")
        try:
            role = SpeakerRole(role_str)
        except ValueError:
            role = SpeakerRole.MINOR

        return CastEntry(
            speaker_id=data.get("speaker_id", data.get("name", "unknown")),
            name=data.get("name", ""),
            aliases=data.get("aliases", []),
            role_level=role,
            profile=CharacterProfile(
                gender=profile_data.get("gender", ""),
                age_range=profile_data.get("age_range", ""),
                profession=profile_data.get("profession", ""),
                personality=profile_data.get("personality", ""),
                speech_style=profile_data.get("speech_style", ""),
                emotional_baseline=baseline,
            ),
            voice_description=data.get("voice_description", ""),
        )

    @staticmethod
    def _merge_registries(existing: list[CastEntry], new: list[CastEntry]) -> list[CastEntry]:
        """Merge new LLM analysis results into existing registry."""
        by_id = {c.speaker_id: c for c in existing}
        for entry in new:
            if entry.speaker_id not in by_id:
                by_id[entry.speaker_id] = entry
            else:
                old = by_id[entry.speaker_id]
                if entry.profile.confidence > old.profile.confidence:
                    by_id[entry.speaker_id] = entry
        return list(by_id.values())
