"""CLI: python -m xspy.agent --input parse_result.json --output screenplay/"""

from __future__ import annotations

from pathlib import Path

import click

from xspy.agent.service import ScreenwriterService
from xspy.core.config import load_llm_models, load_settings
from xspy.core.llm.client import ModelConfig
from xspy.core.llm.prompts import PromptManager
from xspy.core.llm.router import ModelRouter
from xspy.core.logging import setup_logging
from xspy.core.models import ParseResult, ScreenwriterInput


@click.command()
@click.option("--input", "input_file", required=True, type=click.Path(exists=True))
@click.option("--output", "output_dir", default="screenplay")
def main(input_file: str, output_dir: str) -> None:
    """Convert parse result into structured screenplay."""
    setup_logging()
    settings = load_settings()
    llm_data = load_llm_models(settings)
    models = [ModelConfig(**m) for m in llm_data["models"]]
    router = ModelRouter(models, llm_data.get("task_routing", {}))
    prompts = PromptManager()

    parse_result = ParseResult.model_validate_json(Path(input_file).read_text(encoding="utf-8"))

    svc = ScreenwriterService(router, prompts)
    output = svc.process(ScreenwriterInput(parse_result=parse_result))

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for ch in output.screenplay.chapters:
        f = out / f"ch{ch.chapter_index:03d}.json"
        f.write_text(ch.model_dump_json(indent=2), encoding="utf-8")
    (out / "cast_registry.json").write_text(
        output.cast_registry.model_dump_json(indent=2), encoding="utf-8"
    )
    click.echo(f"Generated {len(output.screenplay.chapters)} chapter screenplays → {output_dir}/")


if __name__ == "__main__":
    main()
