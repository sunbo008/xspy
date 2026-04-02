"""CLI: python -m xspy.emotion --input screenplay_ch001.json --cast cast_registry.json --output enriched/"""

from __future__ import annotations

from pathlib import Path

import click

from xspy.core.config import load_llm_models, load_settings
from xspy.core.llm.client import ModelConfig
from xspy.core.llm.prompts import PromptManager
from xspy.core.llm.router import ModelRouter
from xspy.core.logging import setup_logging
from xspy.core.models import CastRegistry, EmotionInput, Screenplay
from xspy.emotion.service import EmotionService


@click.command()
@click.option("--input", "input_dir", required=True, type=click.Path(exists=True))
@click.option("--cast", "cast_file", required=True, type=click.Path(exists=True))
@click.option("--output", "output_dir", default="enriched")
def main(input_dir: str, cast_file: str, output_dir: str) -> None:
    """Infer emotions for screenplay utterances."""
    setup_logging()
    settings = load_settings()
    llm_data = load_llm_models(settings)
    models = [ModelConfig(**m) for m in llm_data["models"]]
    router = ModelRouter(models, llm_data.get("task_routing", {}))
    prompts = PromptManager()

    cast_registry = CastRegistry.model_validate_json(Path(cast_file).read_text(encoding="utf-8"))

    in_path = Path(input_dir)
    from xspy.core.models import ChapterScreenplay

    chapters = []
    for f in sorted(in_path.glob("ch*.json")):
        chapters.append(ChapterScreenplay.model_validate_json(f.read_text(encoding="utf-8")))

    screenplay = Screenplay(chapters=chapters)

    svc = EmotionService(router, prompts)
    enriched = svc.process(EmotionInput(screenplay=screenplay, cast_registry=cast_registry))

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for ch in enriched.chapters:
        f = out / f"ch{ch.chapter_index:03d}.json"
        f.write_text(ch.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"Enriched {len(enriched.chapters)} chapters with emotions → {output_dir}/")


if __name__ == "__main__":
    main()
