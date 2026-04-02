"""CLI: python -m xspy.pipeline --input novel.txt --output audiobook.m4b"""

from __future__ import annotations

import json
from pathlib import Path

import click

from xspy.core.config import load_llm_models, load_settings
from xspy.core.llm.client import ModelConfig
from xspy.core.llm.prompts import PromptManager
from xspy.core.llm.router import ModelRouter
from xspy.core.logging import setup_logging
from xspy.core.models import PipelineInput
from xspy.pipeline.service import PipelineOrchestrator


def _build_orchestrator() -> PipelineOrchestrator:
    """Build the pipeline orchestrator with all dependencies wired."""
    settings = load_settings()
    llm_data = load_llm_models(settings)
    models = [ModelConfig(**m) for m in llm_data["models"]]
    router = ModelRouter(models, llm_data.get("task_routing", {}))
    prompts = PromptManager()

    from xspy.agent.service import ScreenwriterService
    from xspy.audio.service import AudioProcessorService
    from xspy.character.service import CharacterEngineService
    from xspy.emotion.service import EmotionService
    from xspy.parser.service import NovelParserService
    from xspy.tts.service import TTSClientService
    from xspy.voice.service import VoiceBankService

    return PipelineOrchestrator(
        settings=settings,
        parser=NovelParserService(),
        screenwriter=ScreenwriterService(router, prompts),
        character_engine=CharacterEngineService(router, prompts),
        emotion_system=EmotionService(router, prompts),
        voice_bank=VoiceBankService(),
        tts_client=TTSClientService(
            base_url=settings.tts.base_url,
            timeout=settings.tts.timeout_seconds,
            max_retries=settings.tts.max_retries,
        ),
        audio_processor=AudioProcessorService(output_dir=settings.pipeline.output_dir),
    )


@click.command()
@click.option("--input", "input_file", required=True, type=click.Path(exists=True))
@click.option("--chapters", default=None, help="Comma-separated chapter indices to process")
@click.option("--resume/--no-resume", default=True, help="Resume from checkpoint")
def main(input_file: str, chapters: str | None, *, resume: bool) -> None:
    """Run the full novel-to-audiobook pipeline."""
    setup_logging()
    chapter_indices = [int(c.strip()) for c in chapters.split(",")] if chapters else None

    orchestrator = _build_orchestrator()
    result = orchestrator.process(
        PipelineInput(
            novel_file=Path(input_file),
            resume_from_checkpoint=resume,
            chapter_indices=chapter_indices,
        )
    )

    click.echo(f"\nPipeline complete: {result.novel_slug}")
    click.echo(f"  Chapters processed: {result.stats.chapters_processed}")
    click.echo(f"  Total time: {result.stats.total_duration_ms}ms")
    click.echo(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
